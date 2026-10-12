from django.db import transaction
from django.db.models import Q
from io import BytesIO
from django.http import HttpResponse
from openpyxl import Workbook
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from django.core.files.storage import default_storage
from imports.models import ImportBatch, ImportError
from authentication.permissions import RoleBasedPermission
from .importers import validate_asset_batch, import_asset_batch
from .models import Asset, AssetAssignment, AssetCategory, AssetHistory, AssetMaintenance
from .serializers import AssetAssignmentSerializer, AssetCategorySerializer, AssetHistorySerializer, AssetMaintenanceSerializer, AssetSerializer


class AssetCategoryViewSet(viewsets.ModelViewSet):
    queryset = AssetCategory.objects.all()
    serializer_class = AssetCategorySerializer
    permission_classes = [RoleBasedPermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        include_inactive = str(self.request.query_params.get("include_inactive", "false")).lower() == "true"
        if not include_inactive:
            queryset = queryset.filter(is_active=True)
        return queryset


class AssetViewSet(viewsets.ModelViewSet):
    queryset = Asset.objects.select_related("location", "employee", "supplier").prefetch_related("assignments").all()
    serializer_class = AssetSerializer
    permission_classes = [RoleBasedPermission]

    def _asset_snapshot(self, asset):
        return {
            "id": asset.id,
            "asset_code": asset.asset_code,
            "name": asset.name,
            "category": asset.category,
            "manufacturer": asset.manufacturer,
            "model_number": asset.model_number,
            "serial_number": asset.serial_number,
            "purchase_date": asset.purchase_date.isoformat() if asset.purchase_date else None,
            "purchase_cost": str(asset.purchase_cost) if asset.purchase_cost is not None else None,
            "status": asset.status,
            "condition": asset.condition,
            "location_id": asset.location_id,
            "employee_id": asset.employee_id,
            "supplier_id": asset.supplier_id,
        }

    def _create_history(self, asset, event_type, user=None, previous_status="", new_status="", previous_employee=None, new_employee=None, previous_location=None, new_location=None, description="", snapshot=None):
        return AssetHistory.objects.create(
            asset=asset,
            event_type=event_type,
            performed_by=user if getattr(user, "is_authenticated", False) else None,
            previous_status=previous_status or "",
            new_status=new_status or "",
            previous_employee=previous_employee,
            new_employee=new_employee,
            previous_location=previous_location,
            new_location=new_location,
            description=description,
            snapshot=snapshot or self._asset_snapshot(asset),
        )

    def _apply_date_filters(self, queryset):
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        purchase_from = self.request.query_params.get("purchase_date_from")
        purchase_to = self.request.query_params.get("purchase_date_to")
        if date_from:
            queryset = queryset.filter(updated_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(updated_at__date__lte=date_to)
        if purchase_from:
            queryset = queryset.filter(purchase_date__gte=purchase_from)
        if purchase_to:
            queryset = queryset.filter(purchase_date__lte=purchase_to)
        return queryset

    def get_queryset(self):
        queryset = self._apply_date_filters(super().get_queryset())
        status_filter = self.request.query_params.get("status")
        category = self.request.query_params.get("category")
        location = self.request.query_params.get("location")
        search = self.request.query_params.get("search")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if category:
            queryset = queryset.filter(category__icontains=category)
        if location:
            queryset = queryset.filter(location_id=location)
        if search:
            queryset = queryset.filter(Q(asset_code__icontains=search) | Q(name__icontains=search) | Q(serial_number__icontains=search) | Q(manufacturer__icontains=search) | Q(model_number__icontains=search))
        return queryset

    def perform_create(self, serializer):
        asset = serializer.save(status=serializer.validated_data.get("status", Asset.Status.AVAILABLE))
        self._create_history(asset, AssetHistory.EventType.CREATED, self.request.user, new_status=asset.status, new_location=asset.location, description="Asset created.")

    def perform_update(self, serializer):
        old_asset = Asset.objects.select_related("employee", "location").get(pk=serializer.instance.pk)
        previous_status = old_asset.status
        previous_location = old_asset.location
        previous_condition = old_asset.condition
        asset = serializer.save()
        location_changed = old_asset.location_id != asset.location_id
        status_changed = previous_status != asset.status
        condition_changed = previous_condition != asset.condition

        if location_changed:
            previous_name = previous_location.name if previous_location else "Unassigned"
            new_name = asset.location.name if asset.location else "Unassigned"
            self._create_history(asset, AssetHistory.EventType.TRANSFERRED, self.request.user, previous_status=previous_status, new_status=asset.status, previous_location=previous_location, new_location=asset.location, description=f"Asset location transferred from {previous_name} to {new_name}.", snapshot={"previous_location_id": old_asset.location_id, "new_location_id": asset.location_id})

        if status_changed:
            old_label = dict(Asset.Status.choices).get(previous_status, previous_status)
            new_label = dict(Asset.Status.choices).get(asset.status, asset.status)
            event_type = AssetHistory.EventType.RETIRED if asset.status == Asset.Status.RETIRED else AssetHistory.EventType.STATUS_CHANGED
            self._create_history(asset, event_type, self.request.user, previous_status=previous_status, new_status=asset.status, previous_location=previous_location, new_location=asset.location, description=f"Asset status changed from {old_label} to {new_label}.", snapshot={"previous_status": previous_status, "new_status": asset.status})

        if condition_changed:
            old_label = dict(Asset.Condition.choices).get(previous_condition, previous_condition)
            new_label = dict(Asset.Condition.choices).get(asset.condition, asset.condition)
            self._create_history(asset, AssetHistory.EventType.CONDITION_CHANGED, self.request.user, previous_status=previous_status, new_status=asset.status, previous_location=previous_location, new_location=asset.location, description=f"Asset condition changed from {old_label} to {new_label}.", snapshot={"previous_condition": previous_condition, "new_condition": asset.condition})

        if not (location_changed or status_changed or condition_changed):
            self._create_history(asset, AssetHistory.EventType.UPDATED, self.request.user, previous_status=previous_status, new_status=asset.status, previous_location=previous_location, new_location=asset.location, description="Asset information updated.")

    def perform_destroy(self, instance):
        self._create_history(instance, AssetHistory.EventType.DISPOSED, self.request.user, previous_status=instance.status, description="Asset record deleted.", snapshot=self._asset_snapshot(instance))
        instance.delete()

    @action(detail=True, methods=["get"], url_path="detail")
    def asset_detail(self, request, pk=None):
        asset = self.get_object()
        history = asset.history.select_related("performed_by", "previous_employee", "new_employee", "previous_location", "new_location")
        maintenance = asset.maintenance_records.select_related("performed_by")
        assignments = asset.assignments.select_related("employee", "assigned_by", "returned_by")
        return Response({
            "asset": AssetSerializer(asset, context={"request": request}).data,
            "history": AssetHistorySerializer(history, many=True, context={"request": request}).data,
            "assignments": AssetAssignmentSerializer(assignments, many=True, context={"request": request}).data,
            "maintenance": AssetMaintenanceSerializer(maintenance, many=True, context={"request": request}).data,
            "summary": {"history_count": history.count(), "assignment_count": assignments.count(), "maintenance_count": maintenance.count(), "maintenance_cost": sum(record.cost or 0 for record in maintenance)},
        })

    @action(detail=True, methods=["get"], url_path="history")
    def history(self, request, pk=None):
        asset = self.get_object()
        queryset = asset.history.select_related("performed_by", "previous_employee", "new_employee", "previous_location", "new_location")
        if request.query_params.get("date_from"):
            queryset = queryset.filter(event_date__date__gte=request.query_params["date_from"])
        if request.query_params.get("date_to"):
            queryset = queryset.filter(event_date__date__lte=request.query_params["date_to"])
        if request.query_params.get("event_type"):
            queryset = queryset.filter(event_type=request.query_params["event_type"])
        return Response(AssetHistorySerializer(queryset, many=True, context={"request": request}).data)

    @action(detail=True, methods=["get"], url_path="maintenance-history")
    def maintenance_history(self, request, pk=None):
        asset = Asset.objects.filter(pk=pk).first()
        if asset is None:
            return Response({"detail": "Asset not found."}, status=404)
        queryset = AssetMaintenance.objects.filter(asset=asset).select_related("performed_by")
        if request.query_params.get("date_from"):
            queryset = queryset.filter(maintenance_date__gte=request.query_params["date_from"])
        if request.query_params.get("date_to"):
            queryset = queryset.filter(maintenance_date__lte=request.query_params["date_to"])
        return Response(AssetMaintenanceSerializer(queryset, many=True, context={"request": request}).data)

    @action(
        detail=False,
        methods=["post"],
        url_path="import",
        parser_classes=[MultiPartParser, FormParser],
    )
    def import_excel(self, request):
        uploaded_file = request.FILES.get("file")

        if not uploaded_file:
            return Response(
                {
                    "detail": "Please upload an Excel file."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not uploaded_file.name.lower().endswith(
            (".xlsx", ".xlsm")
        ):
            return Response(
                {
                    "detail": (
                        "Only .xlsx or .xlsm Excel files "
                        "are supported."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        batch = ImportBatch.objects.create(
            module=ImportBatch.Module.ASSETS,
            import_type="ASSET_MASTER",
            file_name=uploaded_file.name,
            uploaded_by=request.user,
        )

        try:
            batch = validate_asset_batch(
                batch,
                uploaded_file,
            )
        except Exception as exc:
            batch.status = ImportBatch.Status.FAILED
            batch.save(
                update_fields=["status"]
            )

            return Response(
                {
                    "batch_id": batch.id,
                    "status": batch.status,
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        errors = ImportError.objects.filter(
            batch=batch
        )

        return Response(
            {
                "batch_id": batch.id,
                "status": batch.status,
                "file_name": batch.file_name,
                "total_rows": batch.total_rows,
                "valid_rows": batch.valid_rows,
                "invalid_rows": batch.invalid_rows,
                "errors": [
                    {
                        "row": error.row_number,
                        "column": error.column_name,
                        "code": error.error_code,
                        "message": error.message,
                    }
                    for error in errors
                ],
            },
            status=status.HTTP_200_OK,
        )
    @action(
        detail=False,
        methods=["get"],
        url_path=r"import/(?P<batch_id>[0-9]+)",
    )
    def import_status(self, request, batch_id=None):
        batch = ImportBatch.objects.filter(
            id=batch_id,
            module=ImportBatch.Module.ASSETS,
        ).first()

        if not batch:
            return Response(
                {
                    "detail": "Import batch not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        errors = batch.errors.all().order_by(
            "row_number",
            "id",
        )

        return Response(
            {
                "batch_id": batch.id,
                "module": batch.module,
                "import_type": batch.import_type,
                "file_name": batch.file_name,
                "status": batch.status,
                "total_rows": batch.total_rows,
                "valid_rows": batch.valid_rows,
                "invalid_rows": batch.invalid_rows,
                "imported_rows": batch.imported_rows,
                "created_at": batch.created_at,
                "started_at": batch.started_at,
                "completed_at": batch.completed_at,
                "errors": [
                    {
                        "row": error.row_number,
                        "column": error.column_name,
                        "code": error.error_code,
                        "message": error.message,
                    }
                    for error in errors
                ],
            }
        )
    @action(
        detail=False,
        methods=["post"],
        url_path=r"import/(?P<batch_id>[0-9]+)/confirm",
    )
    def confirm_import(self, request, batch_id=None):
        batch = ImportBatch.objects.filter(
            id=batch_id,
            module=ImportBatch.Module.ASSETS,
        ).first()

        if not batch:
            return Response(
                {
                    "detail": "Import batch not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if batch.uploaded_by_id != request.user.id:
            return Response(
                {
                    "detail": (
                        "You can only confirm your own "
                        "import batches."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if batch.status != ImportBatch.Status.VALIDATED:
            return Response(
                {
                    "detail": (
                        "This import cannot be confirmed. "
                        f"Current status is {batch.status}."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not batch.file:
            return Response(
                {
                    "detail": (
                        "The original Excel file "
                        "could not be found."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            batch.started_at = timezone.now()
            batch.status = ImportBatch.Status.IMPORTING
            batch.save(
                update_fields=[
                    "started_at",
                    "status",
                ]
            )

            batch = import_asset_batch(
                batch,
                batch.file,
            )

        except Exception as exc:
            batch.status = ImportBatch.Status.FAILED
            batch.save(
                update_fields=["status"]
            )

            return Response(
                {
                    "batch_id": batch.id,
                    "status": batch.status,
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "batch_id": batch.id,
                "status": batch.status,
                "total_rows": batch.total_rows,
                "valid_rows": batch.valid_rows,
                "invalid_rows": batch.invalid_rows,
                "imported_rows": batch.imported_rows,
                "completed_at": batch.completed_at,
            },
            status=status.HTTP_200_OK,
        )
    @action(
        detail=False,
        methods=["get"],
        url_path="import-template",
    )
    def import_template(self, request):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Assets"

        headers = [
            "asset_code",
            "name",
            "category",
            "description",
            "manufacturer",
            "model_number",
            "serial_number",
            "purchase_date",
            "purchase_cost",
            "warranty_start",
            "warranty_expiry",
            "status",
            "supplier",
            "location",
            "notes",
        ]

        worksheet.append(headers)

        worksheet.append([
            "AST-0001",
            "Laptop",
            "IT Equipment",
            "Sample asset",
            "Dell",
            "Latitude 5520",
            "SN123456",
            "2026-01-15",
            850000,
            "2026-01-15",
            "2029-01-15",
            "AVAILABLE",
            "",
            "",
            "Sample row - replace or remove",
        ])

        for column in worksheet.columns:
            maximum_length = 0
            column_letter = column[0].column_letter

            for cell in column:
                value = str(cell.value or "")
                maximum_length = max(
                    maximum_length,
                    len(value),
                )

            worksheet.column_dimensions[
                column_letter
            ].width = min(
                maximum_length + 2,
                40,
            )

        output = BytesIO()

        workbook.save(output)
        output.seek(0)

        response = HttpResponse(
            output.getvalue(),
            content_type=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
        )

        response[
            "Content-Disposition"
        ] = 'attachment; filename="asset_import_template.xlsx"'

        return response



class AssetAssignmentViewSet(viewsets.ModelViewSet):
    queryset = AssetAssignment.objects.select_related("asset", "employee", "assigned_by", "returned_by", "asset__location").all()
    serializer_class = AssetAssignmentSerializer
    permission_classes = [RoleBasedPermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        asset = self.request.query_params.get("asset")
        employee = self.request.query_params.get("employee")
        assignment_status = self.request.query_params.get("status")
        if asset:
            queryset = queryset.filter(asset_id=asset)
        if employee:
            queryset = queryset.filter(employee_id=employee)
        if assignment_status:
            queryset = queryset.filter(status=assignment_status)
        return queryset

    @transaction.atomic
    def perform_create(self, serializer):
        asset_id = serializer.validated_data["asset"].id
        asset = Asset.objects.select_for_update().select_related("employee", "location").get(pk=asset_id)
        if asset.status in [Asset.Status.RETIRED, Asset.Status.MAINTENANCE]:
            raise serializers.ValidationError({"asset": "A retired or maintenance asset cannot be assigned."})
        if AssetAssignment.objects.select_for_update().filter(asset=asset, status=AssetAssignment.Status.ACTIVE).exists():
            raise serializers.ValidationError({"asset": "This asset is already assigned."})
        employee = serializer.validated_data["employee"]
        if employee.status != "ACTIVE":
            raise serializers.ValidationError({"employee": "Only active employees can receive assets."})
        previous_status = asset.status
        previous_employee = asset.employee
        assignment = serializer.save(assigned_by=self.request.user, status=AssetAssignment.Status.ACTIVE)
        asset.employee = employee
        asset.status = Asset.Status.ASSIGNED
        asset.save(update_fields=["employee", "status", "updated_at"])
        AssetHistory.objects.create(
            asset=asset,
            event_type=AssetHistory.EventType.ASSIGNED,
            performed_by=self.request.user,
            previous_employee=previous_employee,
            new_employee=employee,
            previous_status=previous_status,
            new_status=asset.status,
            previous_location=asset.location,
            new_location=asset.location,
            description=f"Asset assigned to {assignment.employee.first_name} {assignment.employee.last_name}".strip() + ".",
            snapshot={"assignment_id": assignment.id, "employee_id": employee.id, "assignment_date": str(assignment.assignment_date)},
        )

    @action(detail=True, methods=["post"], url_path="return")
    @transaction.atomic
    def return_asset(self, request, pk=None):
        assignment = AssetAssignment.objects.select_for_update().select_related("asset", "employee").filter(pk=pk).first()
        if assignment is None:
            return Response({"detail": "Assignment not found."}, status=status.HTTP_404_NOT_FOUND)
        if assignment.status != AssetAssignment.Status.ACTIVE:
            return Response({"detail": "Only an active assignment can be returned."}, status=status.HTTP_400_BAD_REQUEST)
        return_date = request.data.get("return_date") or timezone.localdate()
        asset = Asset.objects.select_for_update().get(pk=assignment.asset_id)
        previous_employee = asset.employee
        previous_status = asset.status
        assignment.status = AssetAssignment.Status.RETURNED
        assignment.return_date = return_date
        assignment.returned_by = request.user
        if request.data.get("notes") is not None:
            assignment.notes = request.data.get("notes")
        assignment.save(update_fields=["status", "return_date", "returned_by", "notes", "updated_at"])
        asset.employee = None
        asset.status = Asset.Status.AVAILABLE
        asset.save(update_fields=["employee", "status", "updated_at"])
        AssetHistory.objects.create(
            asset=asset,
            event_type=AssetHistory.EventType.UNASSIGNED,
            performed_by=request.user,
            previous_employee=previous_employee,
            new_employee=None,
            previous_status=previous_status,
            new_status=asset.status,
            previous_location=asset.location,
            new_location=asset.location,
            description=f"Asset returned by {assignment.employee.first_name} {assignment.employee.last_name}".strip() + ".",
            snapshot={"assignment_id": assignment.id, "return_date": str(return_date), "employee_id": assignment.employee_id},
        )
        return Response(AssetAssignmentSerializer(assignment, context={"request": request}).data)

    @action(detail=False, methods=["get"], url_path="current")
    def current(self, request):
        queryset = self.get_queryset().filter(status=AssetAssignment.Status.ACTIVE)
        return Response(AssetAssignmentSerializer(queryset, many=True, context={"request": request}).data)


class AssetMaintenanceViewSet(viewsets.ModelViewSet):
    queryset = AssetMaintenance.objects.select_related("asset", "performed_by").all()
    serializer_class = AssetMaintenanceSerializer
    permission_classes = [RoleBasedPermission]

    def perform_create(self, serializer):
        maintenance = serializer.save(performed_by=self.request.user)
        asset = maintenance.asset
        previous_status = asset.status
        previous_condition = asset.condition
        asset.status = Asset.Status.AVAILABLE
        if maintenance.condition_after:
            asset.condition = maintenance.condition_after
        asset.save(update_fields=["status", "condition", "updated_at"])
        AssetHistory.objects.create(
            asset=asset,
            event_type=AssetHistory.EventType.MAINTENANCE,
            performed_by=self.request.user,
            previous_status=previous_status,
            new_status=asset.status,
            description=f"Maintenance recorded: {maintenance.maintenance_type}. {maintenance.description}".strip(),
            snapshot={"maintenance_id": maintenance.id, "maintenance_type": maintenance.maintenance_type, "maintenance_date": str(maintenance.maintenance_date), "description": maintenance.description, "condition_before": maintenance.condition_before, "condition_after": maintenance.condition_after, "previous_status": previous_status, "new_status": asset.status, "cost": str(maintenance.cost) if maintenance.cost is not None else None},
        )

    def perform_update(self, serializer):
        maintenance = serializer.save(performed_by=self.request.user)
        asset = maintenance.asset
        if maintenance.condition_after:
            asset.condition = maintenance.condition_after
            asset.save(update_fields=["condition", "updated_at"])
