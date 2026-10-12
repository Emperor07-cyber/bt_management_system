from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from openpyxl import Workbook

from imports.models import ImportBatch
from authentication.permissions import RoleBasedPermission

from .models import (
    Vehicle,
    VehicleAssignment,
    VehicleMaintenance,
)

from .serializers import (
    VehicleSerializer,
    VehicleAssignmentSerializer,
    VehicleMaintenanceSerializer,
)

from .importers import (
    validate_vehicle_batch,
    import_vehicle_batch,
)


class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    permission_classes = [RoleBasedPermission]

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
                {"detail": "Excel file is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not uploaded_file.name.lower().endswith(
            (".xlsx", ".xlsm")
        ):
            return Response(
                {"detail": "Only Excel files are supported."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        batch = ImportBatch.objects.create(
            module=ImportBatch.Module.FLEET,
            import_type="VEHICLES",
            file_name=uploaded_file.name,
            uploaded_by=request.user,
        )

        batch.file.save(
            uploaded_file.name,
            uploaded_file,
            save=True,
        )

        batch.file_path = batch.file.name
        batch.save(update_fields=["file_path"])

        try:
            batch = validate_vehicle_batch(
                batch,
                batch.file,
            )
        except Exception as exc:
            batch.status = ImportBatch.Status.FAILED

            batch.errors.create(
                row_number=0,
                error_code="FILE_ERROR",
                message=str(exc),
            )

            batch.save(update_fields=["status"])

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
                "file_name": batch.file_name,
                "total_rows": batch.total_rows,
                "valid_rows": batch.valid_rows,
                "invalid_rows": batch.invalid_rows,
                "errors": [
                    {
                        "row_number": error.row_number,
                        "error_code": error.error_code,
                        "message": error.message,
                    }
                    for error in batch.errors.all()
                ],
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["get"],
        url_path=r"import/(?P<batch_id>[0-9]+)",
    )
    def import_status(self, request, batch_id=None):
        batch = ImportBatch.objects.filter(
            id=batch_id,
            module=ImportBatch.Module.FLEET,
            import_type="VEHICLES",
            uploaded_by=request.user,
        ).first()

        if not batch:
            return Response(
                {"detail": "Import batch not found."},
                status=status.HTTP_404_NOT_FOUND,
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
            module=ImportBatch.Module.FLEET,
            import_type="VEHICLES",
            uploaded_by=request.user,
        ).first()

        if not batch:
            return Response(
                {"detail": "Import batch not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if batch.status != ImportBatch.Status.VALIDATED:
            return Response(
                {
                    "detail": (
                        "Only a successfully validated "
                        "import can be confirmed."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not batch.file:
            return Response(
                {"detail": "Import file is missing."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            batch = import_vehicle_batch(
                batch,
                batch.file,
            )
        except Exception as exc:
            batch.status = ImportBatch.Status.FAILED
            batch.save(update_fields=["status"])

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
                "imported_rows": batch.imported_rows,
            }
        )
    @action(
        detail=False,
        methods=["get"],
        url_path="import-template",
    )
    def import_template(self, request):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Vehicles"

        headers = [
            "registration_number",
            "make",
            "model",
            "year",
            "color",
            "vin",
            "engine_number",
            "vehicle_type",
            "fuel_type",
            "status",
            "purchase_date",
            "purchase_cost",
            "supplier",
            "current_mileage",
            "notes",
        ]

        worksheet.append(headers)

        worksheet.append([
            "ABC-123-XY",
            "Toyota",
            "Hilux",
            2024,
            "White",
            "VIN123456789",
            "ENG123456",
            "Pickup",
            "Diesel",
            "AVAILABLE",
            "2024-01-15",
            45000000,
            "",
            15000,
            "Example vehicle",
        ])

        from django.http import HttpResponse

        response = HttpResponse(
            content_type=(
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml.sheet"
            )
        )

        response[
            "Content-Disposition"
        ] = 'attachment; filename="fleet_vehicle_import_template.xlsx"'

        workbook.save(response)

        return response


class VehicleAssignmentViewSet(viewsets.ModelViewSet):
    queryset = VehicleAssignment.objects.all()
    serializer_class = VehicleAssignmentSerializer
    permission_classes = [RoleBasedPermission]


class VehicleMaintenanceViewSet(viewsets.ModelViewSet):
    queryset = VehicleMaintenance.objects.all()
    serializer_class = VehicleMaintenanceSerializer
    permission_classes = [RoleBasedPermission]