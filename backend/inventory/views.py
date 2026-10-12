from django.db import transaction
from django.utils import timezone
from django.db.models import Case, F, IntegerField, Q, Sum, When
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from authentication.permissions import RoleBasedPermission

from django.core.files.uploadedfile import UploadedFile
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from imports.models import ImportBatch

from .importers import (
    import_item_batch,
    import_opening_stock_batch,
    validate_item_batch,
    validate_opening_stock_batch,
)

from .models import (
    Category,
    InventoryUnit,
    InventoryUnitHistory,
    Item,
    StockTransaction,
    StockTransfer,
    Stocktake,
    StocktakeLine,
)

from .serializers import (
    CategorySerializer,
    InventoryUnitHistorySerializer,
    InventoryUnitSerializer,
    ItemSerializer,
    StockTransactionSerializer,
    StockTransferSerializer,
    StocktakeSerializer,
    StocktakeLineSerializer,
)


# ============================================================
# CATEGORY
# ============================================================

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [RoleBasedPermission]

    def get_queryset(self):
        queryset = super().get_queryset()

        search = self.request.query_params.get("search")
        is_active = self.request.query_params.get("is_active")

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
            )

        if is_active is not None:
            queryset = queryset.filter(
                is_active=is_active.lower() == "true"
            )

        return queryset


# ============================================================
# ITEM
# ============================================================

class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.select_related(
        "category",
        "supplier",
    ).all()

    serializer_class = ItemSerializer
    permission_classes = [RoleBasedPermission]

    def get_queryset(self):
        queryset = super().get_queryset()

        search = self.request.query_params.get("search")
        category = self.request.query_params.get("category")
        supplier = self.request.query_params.get("supplier")
        is_active = self.request.query_params.get("is_active")
        stock_status = self.request.query_params.get("stock_status")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        # ----------------------------------------------------
        # SEARCH
        # ----------------------------------------------------

        if search:
            queryset = queryset.filter(
                Q(item_code__icontains=search)
                | Q(name__icontains=search)
                | Q(brand__icontains=search)
                | Q(model_number__icontains=search)
            )

        # ----------------------------------------------------
        # CATEGORY
        # ----------------------------------------------------

        if category:
            queryset = queryset.filter(
                category_id=category
            )

        # ----------------------------------------------------
        # SUPPLIER
        # ----------------------------------------------------

        if supplier:
            queryset = queryset.filter(
                supplier_id=supplier
            )

        # ----------------------------------------------------
        # ACTIVE STATUS
        # ----------------------------------------------------

        if is_active is not None:
            queryset = queryset.filter(
                is_active=is_active.lower() == "true"
            )

        # ----------------------------------------------------
        # DATE FILTER
        # ----------------------------------------------------

        if date_from:
            queryset = queryset.filter(
                created_at__date__gte=date_from
            )

        if date_to:
            queryset = queryset.filter(
                created_at__date__lte=date_to
            )

        # ----------------------------------------------------
        # STOCK STATUS
        #
        # This is currently evaluated in Python because
        # current_stock is a calculated property.
        # ----------------------------------------------------

        if stock_status:
            filtered_ids = []

            for item in queryset:
                if item.stock_status == stock_status:
                    filtered_ids.append(item.id)

            queryset = queryset.filter(
                id__in=filtered_ids
            )

        return queryset

    # ========================================================
    # ITEM DETAIL
    # ========================================================

    @action(
        detail=True,
        methods=["get"],
        url_path="detail",
    )
    def item_detail(self, request, pk=None):
        """
        Returns a complete inventory-item profile including:

        - item information
        - current stock
        - stock status
        - transactions
        - transfers
        - inventory units
        """

        item = self.get_object()

        transactions = (
            item.stock_transactions
            .select_related(
                "employee",
                "location",
                "created_by",
            )
            .order_by("-created_at")
        )

        transfers = (
            item.stock_transfers
            .select_related(
                "source_location",
                "destination_location",
                "transferred_by",
            )
            .order_by("-created_at")
        )

        units = (
            item.units
            .select_related(
                "location",
                "assigned_to",
            )
            .order_by("asset_number")
        )

        return Response(
            {
                "item": ItemSerializer(
                    item,
                    context={"request": request},
                ).data,

                "stock": {
                    "current_stock": item.current_stock,
                    "stock_status": item.stock_status,
                    "reorder_level": item.reorder_level,
                    "minimum_stock": item.minimum_stock,
                },

                "transactions": StockTransactionSerializer(
                    transactions,
                    many=True,
                    context={"request": request},
                ).data,

                "transfers": StockTransferSerializer(
                    transfers,
                    many=True,
                    context={"request": request},
                ).data,

                "units": InventoryUnitSerializer(
                    units,
                    many=True,
                    context={"request": request},
                ).data,
            }
        )

    # ========================================================
    # ITEM TRANSACTION HISTORY
    # ========================================================

    @action(
        detail=True,
        methods=["get"],
        url_path="transactions",
    )
    def transactions(self, request, pk=None):
        """
        Returns transaction history for a specific item.

        Supported filters:

        ?transaction_type=RECEIVED
        ?transaction_type=ISSUED
        ?transaction_type=RETURNED
        ?transaction_type=ADJUSTMENT

        ?location=1
        ?employee=2

        ?date_from=2026-01-01
        ?date_to=2026-12-31
        """

        item = self.get_object()

        queryset = (
            item.stock_transactions
            .select_related(
                "employee",
                "location",
                "created_by",
            )
            .order_by("-created_at")
        )

        transaction_type = request.query_params.get(
            "transaction_type"
        )

        location = request.query_params.get(
            "location"
        )

        employee = request.query_params.get(
            "employee"
        )

        date_from = request.query_params.get(
            "date_from"
        )

        date_to = request.query_params.get(
            "date_to"
        )

        if transaction_type:
            queryset = queryset.filter(
                transaction_type=transaction_type
            )

        if location:
            queryset = queryset.filter(
                location_id=location
            )

        if employee:
            queryset = queryset.filter(
                employee_id=employee
            )

        if date_from:
            queryset = queryset.filter(
                created_at__date__gte=date_from
            )

        if date_to:
            queryset = queryset.filter(
                created_at__date__lte=date_to
            )

        serializer = StockTransactionSerializer(
            queryset,
            many=True,
            context={"request": request},
        )

        return Response(serializer.data)

    # ========================================================
    # STOCK SUMMARY
    # ========================================================

    @action(
        detail=True,
        methods=["get"],
        url_path="stock-summary",
    )
    def stock_summary(self, request, pk=None):
        """
        Returns total stock and location-level stock
        for one inventory item.
        """

        item = self.get_object()

        locations = {}

        location_ids = (
            item.stock_transactions
            .exclude(location=None)
            .values_list(
                "location_id",
                flat=True,
            )
            .distinct()
        )

        for location_id in location_ids:

            transactions = item.stock_transactions.filter(
                location_id=location_id
            )

            stock = transactions.aggregate(
                total=Sum(
                    Case(
                        When(
                            transaction_type__in=[
                                StockTransaction
                                .TransactionType
                                .RECEIVED,

                                StockTransaction
                                .TransactionType
                                .RETURNED,
                            ],
                            then="quantity",
                        ),

                        When(
                            transaction_type=(
                                StockTransaction
                                .TransactionType
                                .ISSUED
                            ),
                            then=-F("quantity"),
                        ),

                        When(
                            transaction_type=(
                                StockTransaction
                                .TransactionType
                                .ADJUSTMENT
                            ),
                            then="quantity",
                        ),

                        default=0,

                        output_field=IntegerField(),
                    )
                )
            )["total"] or 0

            locations[str(location_id)] = stock

        return Response(
            {
                "item_id": item.id,
                "item_code": item.item_code,
                "current_stock": item.current_stock,
                "stock_status": item.stock_status,
                "reorder_level": item.reorder_level,
                "minimum_stock": item.minimum_stock,
                "locations": locations,
            }
        )

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
            module=ImportBatch.Module.INVENTORY,
            import_type="ITEMS",
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
            batch = validate_item_batch(
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
                        "column_name": error.column_name,
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
            module=ImportBatch.Module.INVENTORY,
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
            module=ImportBatch.Module.INVENTORY,
            import_type="ITEMS",
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
            batch = import_item_batch(
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


# ============================================================
# INVENTORY UNIT
# ============================================================

class InventoryUnitViewSet(viewsets.ModelViewSet):
    queryset = InventoryUnit.objects.select_related(
        "item",
        "location",
        "assigned_to",
    ).all()

    serializer_class = InventoryUnitSerializer
    permission_classes = [RoleBasedPermission]

    def get_queryset(self):
        queryset = super().get_queryset()

        search = self.request.query_params.get(
            "search"
        )

        status_filter = self.request.query_params.get(
            "status"
        )

        condition = self.request.query_params.get(
            "condition"
        )

        location = self.request.query_params.get(
            "location"
        )

        employee = self.request.query_params.get(
            "employee"
        )

        item = self.request.query_params.get(
            "item"
        )

        if search:
            queryset = queryset.filter(
                Q(asset_number__icontains=search)
                | Q(serial_number__icontains=search)
            )

        if status_filter:
            queryset = queryset.filter(
                status=status_filter
            )

        if condition:
            queryset = queryset.filter(
                condition=condition
            )

        if location:
            queryset = queryset.filter(
                location_id=location
            )

        if employee:
            queryset = queryset.filter(
                assigned_to_id=employee
            )

        if item:
            queryset = queryset.filter(
                item_id=item
            )

        return queryset

    # ========================================================
    # HISTORY HELPER
    # ========================================================

    def _create_history(
        self,
        unit,
        event_type,
        user,
        previous_status="",
        new_status="",
        previous_condition="",
        new_condition="",
        previous_location=None,
        new_location=None,
        previous_employee=None,
        new_employee=None,
        description="",
    ):
        return InventoryUnitHistory.objects.create(
            unit=unit,

            event_type=event_type,

            performed_by=user,

            previous_status=previous_status or "",

            new_status=new_status or "",

            previous_condition=previous_condition or "",

            new_condition=new_condition or "",

            previous_location=previous_location,

            new_location=new_location,

            previous_employee=previous_employee,

            new_employee=new_employee,

            description=description,

            snapshot={
                "asset_number": unit.asset_number,
                "item_id": unit.item_id,
                "status": unit.status,
                "condition": unit.condition,
                "location_id": unit.location_id,
                "assigned_to_id": unit.assigned_to_id,
            },
        )

    # ========================================================
    # CREATE UNIT
    # ========================================================

    def perform_create(self, serializer):
        unit = serializer.save()

        self._create_history(
            unit=unit,

            event_type=(
                InventoryUnitHistory
                .EventType
                .CREATED
            ),

            user=self.request.user,

            new_status=unit.status,

            new_condition=unit.condition,

            new_location=unit.location,

            new_employee=unit.assigned_to,

            description="Inventory unit created.",
        )

    # ========================================================
    # UPDATE UNIT
    # ========================================================

    def perform_update(self, serializer):

        old_unit = (
            InventoryUnit.objects
            .select_related(
                "location",
                "assigned_to",
            )
            .get(
                pk=serializer.instance.pk
            )
        )

        previous_status = old_unit.status
        previous_condition = old_unit.condition
        previous_location = old_unit.location
        previous_employee = old_unit.assigned_to

        unit = serializer.save()

        # ----------------------------------------------------
        # EMPLOYEE CHANGE
        # ----------------------------------------------------

        employee_changed = (
            previous_employee.id
            if previous_employee
            else None
        ) != (
            unit.assigned_to.id
            if unit.assigned_to
            else None
        )

        # ----------------------------------------------------
        # LOCATION CHANGE
        # ----------------------------------------------------

        location_changed = (
            previous_location.id
            if previous_location
            else None
        ) != (
            unit.location.id
            if unit.location
            else None
        )

        # ----------------------------------------------------
        # STATUS CHANGE
        # ----------------------------------------------------

        status_changed = (
            previous_status != unit.status
        )

        # ----------------------------------------------------
        # CONDITION CHANGE
        # ----------------------------------------------------

        condition_changed = (
            previous_condition != unit.condition
        )

        # ----------------------------------------------------
        # EMPLOYEE HISTORY
        # ----------------------------------------------------

        if employee_changed:

            event_type = (
                InventoryUnitHistory
                .EventType
                .ASSIGNED
                if unit.assigned_to
                else
                InventoryUnitHistory
                .EventType
                .UNASSIGNED
            )

            description = (
                "Inventory unit assigned."
                if unit.assigned_to
                else
                "Inventory unit unassigned."
            )

            self._create_history(
                unit=unit,

                event_type=event_type,

                user=self.request.user,

                previous_status=previous_status,

                new_status=unit.status,

                previous_condition=previous_condition,

                new_condition=unit.condition,

                previous_location=previous_location,

                new_location=unit.location,

                previous_employee=previous_employee,

                new_employee=unit.assigned_to,

                description=description,
            )

        # ----------------------------------------------------
        # LOCATION HISTORY
        # ----------------------------------------------------

        if location_changed:

            self._create_history(
                unit=unit,

                event_type=(
                    InventoryUnitHistory
                    .EventType
                    .TRANSFERRED
                ),

                user=self.request.user,

                previous_status=previous_status,

                new_status=unit.status,

                previous_condition=previous_condition,

                new_condition=unit.condition,

                previous_location=previous_location,

                new_location=unit.location,

                previous_employee=previous_employee,

                new_employee=unit.assigned_to,

                description=(
                    "Inventory unit location transferred."
                ),
            )

        # ----------------------------------------------------
        # STATUS HISTORY
        # ----------------------------------------------------

        if status_changed:

            if (
                unit.status
                == InventoryUnit.Status.DISPOSED
            ):
                event_type = (
                    InventoryUnitHistory
                    .EventType
                    .DISPOSED
                )

            elif (
                unit.status
                == InventoryUnit.Status.LOST
            ):
                event_type = (
                    InventoryUnitHistory
                    .EventType
                    .LOST
                )

            else:
                event_type = (
                    InventoryUnitHistory
                    .EventType
                    .STATUS_CHANGED
                )

            self._create_history(
                unit=unit,

                event_type=event_type,

                user=self.request.user,

                previous_status=previous_status,

                new_status=unit.status,

                previous_condition=previous_condition,

                new_condition=unit.condition,

                previous_location=previous_location,

                new_location=unit.location,

                previous_employee=previous_employee,

                new_employee=unit.assigned_to,

                description=(
                    "Inventory unit status changed "
                    f"from {previous_status} "
                    f"to {unit.status}."
                ),
            )

        # ----------------------------------------------------
        # CONDITION HISTORY
        # ----------------------------------------------------

        if condition_changed:

            self._create_history(
                unit=unit,

                event_type=(
                    InventoryUnitHistory
                    .EventType
                    .CONDITION_CHANGED
                ),

                user=self.request.user,

                previous_status=previous_status,

                new_status=unit.status,

                previous_condition=previous_condition,

                new_condition=unit.condition,

                previous_location=previous_location,

                new_location=unit.location,

                previous_employee=previous_employee,

                new_employee=unit.assigned_to,

                description=(
                    "Inventory unit condition changed "
                    f"from {previous_condition} "
                    f"to {unit.condition}."
                ),
            )

        # ----------------------------------------------------
        # GENERIC UPDATE HISTORY
        # ----------------------------------------------------

        if not (
            employee_changed
            or location_changed
            or status_changed
            or condition_changed
        ):

            self._create_history(
                unit=unit,

                event_type=(
                    InventoryUnitHistory
                    .EventType
                    .UPDATED
                ),

                user=self.request.user,

                previous_status=previous_status,

                new_status=unit.status,

                previous_condition=previous_condition,

                new_condition=unit.condition,

                previous_location=previous_location,

                new_location=unit.location,

                previous_employee=previous_employee,

                new_employee=unit.assigned_to,

                description=(
                    "Inventory unit information updated."
                ),
            )

    # ========================================================
    # UNIT HISTORY
    # ========================================================

    @action(
        detail=True,
        methods=["get"],
        url_path="history",
    )
    def history(self, request, pk=None):

        unit = self.get_object()

        queryset = (
            unit.history
            .select_related(
                "performed_by",
                "previous_location",
                "new_location",
                "previous_employee",
                "new_employee",
            )
            .order_by("-event_date")
        )

        date_from = request.query_params.get(
            "date_from"
        )

        date_to = request.query_params.get(
            "date_to"
        )

        if date_from:
            queryset = queryset.filter(
                event_date__date__gte=date_from
            )

        if date_to:
            queryset = queryset.filter(
                event_date__date__lte=date_to
            )

        serializer = InventoryUnitHistorySerializer(
            queryset,
            many=True,
            context={"request": request},
        )

        return Response(serializer.data)


# ============================================================
# STOCK TRANSACTIONS
# ============================================================

class StockTransactionViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Stock transactions are ledger entries.

    Supported:

        POST  /transactions/
        GET   /transactions/
        GET   /transactions/<id>/

    Update and delete are deliberately not exposed.

    Corrections should be made using ADJUSTMENT transactions.
    """

    queryset = StockTransaction.objects.select_related(
        "item",
        "employee",
        "location",
        "created_by",
    ).all()

    serializer_class = StockTransactionSerializer
    permission_classes = [RoleBasedPermission]

    def get_queryset(self):
        queryset = super().get_queryset()

        item = self.request.query_params.get(
            "item"
        )

        transaction_type = (
            self.request.query_params.get(
                "transaction_type"
            )
        )

        location = self.request.query_params.get(
            "location"
        )

        employee = self.request.query_params.get(
            "employee"
        )

        date_from = self.request.query_params.get(
            "date_from"
        )

        date_to = self.request.query_params.get(
            "date_to"
        )

        search = self.request.query_params.get(
            "search"
        )

        if item:
            queryset = queryset.filter(
                item_id=item
            )

        if transaction_type:
            queryset = queryset.filter(
                transaction_type=transaction_type
            )

        if location:
            queryset = queryset.filter(
                location_id=location
            )

        if employee:
            queryset = queryset.filter(
                employee_id=employee
            )

        if date_from:
            queryset = queryset.filter(
                created_at__date__gte=date_from
            )

        if date_to:
            queryset = queryset.filter(
                created_at__date__lte=date_to
            )

        if search:
            queryset = queryset.filter(
                Q(reference__icontains=search)
                | Q(notes__icontains=search)
                | Q(
                    item__item_code__icontains=search
                )
                | Q(
                    item__name__icontains=search
                )
            )

        return queryset

    # ========================================================
    # CREATE TRANSACTION
    # ========================================================

    def perform_create(self, serializer):

        requested_item = (
            serializer.validated_data["item"]
        )

        transaction_type = (
            serializer.validated_data[
                "transaction_type"
            ]
        )

        quantity = (
            serializer.validated_data[
                "quantity"
            ]
        )

        location = (
            serializer.validated_data.get(
                "location"
            )
        )

        with transaction.atomic():

            # ------------------------------------------------
            # Lock the item.
            #
            # This prevents two simultaneous stock issues
            # from both consuming the same stock.
            # ------------------------------------------------

            locked_item = (
                Item.objects
                .select_for_update()
                .get(
                    pk=requested_item.pk
                )
            )

            # ------------------------------------------------
            # Inactive items cannot receive new movement.
            # ------------------------------------------------

            if not locked_item.is_active:

                raise ValidationError(
                    {
                        "item": (
                            "Transactions cannot be "
                            "created for an inactive "
                            "inventory item."
                        )
                    }
                )

            # ------------------------------------------------
            # ISSUE - GLOBAL STOCK CHECK
            # ------------------------------------------------

            if (
                transaction_type
                == StockTransaction
                .TransactionType
                .ISSUED
            ):

                if quantity > locked_item.current_stock:

                    raise ValidationError(
                        {
                            "quantity": (
                                "Insufficient stock. "
                                f"Available stock is "
                                f"{locked_item.current_stock}."
                            )
                        }
                    )

            # ------------------------------------------------
            # ISSUE - LOCATION STOCK CHECK
            # ------------------------------------------------

            if (
                transaction_type
                == StockTransaction
                .TransactionType
                .ISSUED
                and location is not None
            ):

                location_stock = (
                    StockTransaction.objects
                    .filter(
                        item=locked_item,
                        location=location,
                    )
                    .aggregate(
                        total=Sum(
                            Case(
                                When(
                                    transaction_type__in=[
                                        StockTransaction
                                        .TransactionType
                                        .RECEIVED,

                                        StockTransaction
                                        .TransactionType
                                        .RETURNED,
                                    ],
                                    then="quantity",
                                ),

                                When(
                                    transaction_type=(
                                        StockTransaction
                                        .TransactionType
                                        .ISSUED
                                    ),
                                    then=-F("quantity"),
                                ),

                                When(
                                    transaction_type=(
                                        StockTransaction
                                        .TransactionType
                                        .ADJUSTMENT
                                    ),
                                    then="quantity",
                                ),

                                default=0,

                                output_field=IntegerField(),
                            )
                        )
                    )["total"] or 0
                )

                if quantity > location_stock:

                    raise ValidationError(
                        {
                            "quantity": (
                                "Insufficient stock at "
                                "the selected location. "
                                f"Available stock is "
                                f"{location_stock}."
                            )
                        }
                    )

            # ------------------------------------------------
            # NEGATIVE ADJUSTMENT
            # ------------------------------------------------

            if (
                transaction_type
                == StockTransaction
                .TransactionType
                .ADJUSTMENT
                and quantity < 0
            ):

                if location is not None:

                    available_stock = (
                        StockTransaction.objects
                        .filter(
                            item=locked_item,
                            location=location,
                        )
                        .aggregate(
                            total=Sum(
                                Case(
                                    When(
                                        transaction_type__in=[
                                            StockTransaction
                                            .TransactionType
                                            .RECEIVED,

                                            StockTransaction
                                            .TransactionType
                                            .RETURNED,
                                        ],
                                        then="quantity",
                                    ),

                                    When(
                                        transaction_type=(
                                            StockTransaction
                                            .TransactionType
                                            .ISSUED
                                        ),
                                        then=-F("quantity"),
                                    ),

                                    When(
                                        transaction_type=(
                                            StockTransaction
                                            .TransactionType
                                            .ADJUSTMENT
                                        ),
                                        then="quantity",
                                    ),

                                    default=0,

                                    output_field=IntegerField(),
                                )
                            )
                        )["total"] or 0
                    )

                else:
                    available_stock = (
                        locked_item.current_stock
                    )

                if abs(quantity) > available_stock:

                    raise ValidationError(
                        {
                            "quantity": (
                                "Adjustment would make "
                                "stock negative. "
                                f"Available stock is "
                                f"{available_stock}."
                            )
                        }
                    )

            # ------------------------------------------------
            # CREATE LEDGER ENTRY
            # ------------------------------------------------

            serializer.save(
                item=locked_item,
                created_by=self.request.user,
            )

    @action(
        detail=False,
        methods=["post"],
        url_path="import-opening-stock",
        parser_classes=[MultiPartParser, FormParser],
    )
    def import_opening_stock(self, request):
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
            module=ImportBatch.Module.INVENTORY,
            import_type="OPENING_STOCK",
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
            batch = validate_opening_stock_batch(
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
        methods=["post"],
        url_path=r"import-opening-stock/(?P<batch_id>[0-9]+)/confirm",
    )
    def confirm_opening_stock_import(
        self,
        request,
        batch_id=None,
    ):
        batch = ImportBatch.objects.filter(
            id=batch_id,
            module=ImportBatch.Module.INVENTORY,
            import_type="OPENING_STOCK",
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
            batch = import_opening_stock_batch(
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


# ============================================================
# STOCKTAKING
# ============================================================

def _location_stock(item_id, location_id):
    return (
        StockTransaction.objects
        .filter(
            item_id=item_id,
            location_id=location_id,
        )
        .aggregate(
            total=Sum(
                Case(
                    When(
                        transaction_type__in=[
                            StockTransaction.TransactionType.RECEIVED,
                            StockTransaction.TransactionType.RETURNED,
                        ],
                        then="quantity",
                    ),
                    When(
                        transaction_type=(
                            StockTransaction.TransactionType.ISSUED
                        ),
                        then=-F("quantity"),
                    ),
                    When(
                        transaction_type=(
                            StockTransaction.TransactionType.ADJUSTMENT
                        ),
                        then="quantity",
                    ),
                    default=0,
                    output_field=IntegerField(),
                )
            )
        )["total"] or 0
    )


class StocktakeViewSet(viewsets.ModelViewSet):
    queryset = Stocktake.objects.select_related(
        "location",
        "created_by",
        "completed_by",
    ).prefetch_related("lines__item")

    serializer_class = StocktakeSerializer
    permission_classes = [RoleBasedPermission]

    def get_queryset(self):
        queryset = super().get_queryset()

        location = self.request.query_params.get(
            "location"
        )

        status_filter = self.request.query_params.get(
            "status"
        )

        search = self.request.query_params.get(
            "search"
        )

        date_from = self.request.query_params.get(
            "date_from"
        )

        date_to = self.request.query_params.get(
            "date_to"
        )

        if location:
            queryset = queryset.filter(
                location_id=location
            )

        if status_filter:
            queryset = queryset.filter(
                status=status_filter
            )

        if search:
            queryset = queryset.filter(
                Q(reference__icontains=search)
                | Q(notes__icontains=search)
                | Q(location__name__icontains=search)
                | Q(
                    location__location_code__icontains=search
                )
            )

        if date_from:
            queryset = queryset.filter(
                created_at__date__gte=date_from
            )

        if date_to:
            queryset = queryset.filter(
                created_at__date__lte=date_to
            )

        return queryset

    def create(
        self,
        request,
        *args,
        **kwargs,
    ):
        """
        Create a stocktake and snapshot location stock
        into its lines.

        Optional item_ids limits the stocktake to selected
        active items.

        If omitted, all active inventory items are included.
        """

        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        location = serializer.validated_data[
            "location"
        ]

        item_ids = request.data.get(
            "item_ids"
        )

        if isinstance(item_ids, str):
            item_ids = [
                value.strip()
                for value in item_ids.split(",")
                if value.strip()
            ]

        elif (
            item_ids is not None
            and not isinstance(item_ids, list)
        ):
            raise ValidationError(
                {
                    "item_ids": (
                        "item_ids must be a list "
                        "of item IDs."
                    )
                }
            )

        items = Item.objects.filter(
            is_active=True
        )

        if item_ids:

            try:
                item_ids = [
                    int(value)
                    for value in item_ids
                ]

            except (
                TypeError,
                ValueError,
            ):
                raise ValidationError(
                    {
                        "item_ids": (
                            "item_ids must contain "
                            "valid integer IDs."
                        )
                    }
                )

            items = items.filter(
                id__in=item_ids
            )

        items = list(
            items.order_by("name")
        )

        if not items:
            raise ValidationError(
                {
                    "item_ids": (
                        "No active inventory items "
                        "were selected."
                    )
                }
            )

        with transaction.atomic():

            stocktake = serializer.save(
                created_by=request.user
            )

            StocktakeLine.objects.bulk_create(
                [
                    StocktakeLine(
                        stocktake=stocktake,
                        item=item,
                        system_quantity=_location_stock(
                            item.id,
                            location.id,
                        ),
                    )
                    for item in items
                ]
            )

        stocktake = self.get_queryset().get(
            pk=stocktake.pk
        )

        return Response(
            self.get_serializer(
                stocktake
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="start",
    )
    def start(
        self,
        request,
        pk=None,
    ):
        with transaction.atomic():

            stocktake = (
                Stocktake.objects
                .select_for_update()
                .get(pk=pk)
            )

            if stocktake.status != Stocktake.Status.DRAFT:
                raise ValidationError(
                    {
                        "status": (
                            "Only a draft stocktake "
                            "can be started."
                        )
                    }
                )

            stocktake.status = (
                Stocktake.Status.IN_PROGRESS
            )

            stocktake.save(
                update_fields=["status"]
            )

        return Response(
            self.get_serializer(
                self.get_queryset().get(pk=pk)
            ).data
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="confirm",
    )
    def confirm(
        self,
        request,
        pk=None,
    ):
        with transaction.atomic():

            stocktake = (
                Stocktake.objects
                .select_for_update()
                .select_related("location")
                .get(pk=pk)
            )

            if stocktake.status not in [
                Stocktake.Status.DRAFT,
                Stocktake.Status.IN_PROGRESS,
            ]:
                raise ValidationError(
                    {
                        "status": (
                            "Only an open stocktake "
                            "can be confirmed."
                        )
                    }
                )

            lines = list(
                stocktake.lines
                .select_related("item")
                .select_for_update()
                .order_by("item__name")
            )

            if not lines:
                raise ValidationError(
                    {
                        "lines": (
                            "A stocktake must contain "
                            "at least one item."
                        )
                    }
                )

            uncounted = [
                line.item.item_code
                for line in lines
                if line.counted_quantity is None
            ]

            if uncounted:
                raise ValidationError(
                    {
                        "counted_quantity": (
                            "All lines must be counted "
                            "before confirmation: "
                            f"{', '.join(uncounted)}."
                        )
                    }
                )

            # Lock every affected item before reading
            # current stock.
            locked_items = {
                item.id: item
                for item in (
                    Item.objects
                    .select_for_update()
                    .filter(
                        id__in=[
                            line.item_id
                            for line in lines
                        ]
                    )
                )
            }

            adjustments = []

            for line in lines:

                current_stock = _location_stock(
                    line.item_id,
                    stocktake.location_id,
                )

                if current_stock != line.system_quantity:
                    raise ValidationError(
                        {
                            "stock_changed": (
                                f"{line.item.item_code}: "
                                "system stock changed from "
                                f"{line.system_quantity} "
                                f"to {current_stock} since "
                                "the stocktake snapshot. "
                                "Refresh or create a new "
                                "stocktake before confirming."
                            )
                        }
                    )

                variance = (
                    line.counted_quantity
                    - line.system_quantity
                )

                line.variance = variance

                line.counted_at = (
                    line.counted_at
                    or timezone.now()
                )

                line.save(
                    update_fields=[
                        "variance",
                        "counted_at",
                    ]
                )

                if variance:

                    new_stock = (
                        current_stock
                        + variance
                    )

                    if new_stock < 0:
                        raise ValidationError(
                            {
                                "counted_quantity": (
                                    f"{line.item.item_code}: "
                                    "counted quantity would "
                                    "make location stock "
                                    "negative."
                                )
                            }
                        )

                    adjustments.append(
                        StockTransaction(
                            item=locked_items[
                                line.item_id
                            ],

                            transaction_type=(
                                StockTransaction
                                .TransactionType
                                .ADJUSTMENT
                            ),

                            quantity=variance,

                            reference=(
                                f"{stocktake.reference}-"
                                f"{line.item.item_code}"
                            ),

                            notes=(
                                "Physical stocktake "
                                f"adjustment for "
                                f"{stocktake.reference}. "
                                f"System={line.system_quantity}; "
                                f"Counted={line.counted_quantity}."
                            ),

                            location=stocktake.location,

                            created_by=request.user,
                        )
                    )

            StockTransaction.objects.bulk_create(
                adjustments
            )

            stocktake.status = (
                Stocktake.Status.COMPLETED
            )

            stocktake.completed_at = (
                timezone.now()
            )

            stocktake.completed_by = (
                request.user
            )

            stocktake.save(
                update_fields=[
                    "status",
                    "completed_at",
                    "completed_by",
                ]
            )

        stocktake = self.get_queryset().get(
            pk=pk
        )

        return Response(
            self.get_serializer(
                stocktake
            ).data
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="cancel",
    )
    def cancel(
        self,
        request,
        pk=None,
    ):
        with transaction.atomic():

            stocktake = (
                Stocktake.objects
                .select_for_update()
                .get(pk=pk)
            )

            if stocktake.status == (
                Stocktake.Status.COMPLETED
            ):
                raise ValidationError(
                    {
                        "status": (
                            "A completed stocktake "
                            "cannot be cancelled."
                        )
                    }
                )

            if stocktake.status == (
                Stocktake.Status.CANCELLED
            ):
                raise ValidationError(
                    {
                        "status": (
                            "Stocktake is already "
                            "cancelled."
                        )
                    }
                )

            stocktake.status = (
                Stocktake.Status.CANCELLED
            )

            stocktake.save(
                update_fields=["status"]
            )

        return Response(
            self.get_serializer(
                self.get_queryset().get(pk=pk)
            ).data
        )


class StocktakeLineViewSet(
    viewsets.ModelViewSet
):
    queryset = (
        StocktakeLine.objects
        .select_related(
            "stocktake",
            "item",
            "stocktake__location",
        )
    )

    serializer_class = StocktakeLineSerializer
    permission_classes = [RoleBasedPermission]

    def get_queryset(self):
        queryset = super().get_queryset()

        stocktake = (
            self.request.query_params.get(
                "stocktake"
            )
        )

        if stocktake:
            queryset = queryset.filter(
                stocktake_id=stocktake
            )

        return queryset

    def partial_update(
        self,
        request,
        *args,
        **kwargs,
    ):
        line = self.get_object()

        if line.stocktake.status in [
            Stocktake.Status.COMPLETED,
            Stocktake.Status.CANCELLED,
        ]:
            raise ValidationError(
                {
                    "status": (
                        "Closed stocktake lines "
                        "cannot be changed."
                    )
                }
            )

        return super().partial_update(
            request,
            *args,
            **kwargs,
        )

    def update(
        self,
        request,
        *args,
        **kwargs,
    ):
        line = self.get_object()

        if line.stocktake.status in [
            Stocktake.Status.COMPLETED,
            Stocktake.Status.CANCELLED,
        ]:
            raise ValidationError(
                {
                    "status": (
                        "Closed stocktake lines "
                        "cannot be changed."
                    )
                }
            )

        return super().update(
            request,
            *args,
            **kwargs,
        )


# ============================================================
# STOCK TRANSFERS
# ============================================================

class StockTransferViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Stock transfers are atomic operations.

    One transfer produces:

        SOURCE       -> ISSUE
        DESTINATION  -> RECEIVED

    Therefore global stock stays unchanged while
    location stock changes.
    """

    queryset = StockTransfer.objects.select_related(
        "item",
        "source_location",
        "destination_location",
        "transferred_by",
    ).all()

    serializer_class = StockTransferSerializer
    permission_classes = [RoleBasedPermission]

    def get_queryset(self):
        queryset = super().get_queryset()

        item = self.request.query_params.get(
            "item"
        )

        source = self.request.query_params.get(
            "source_location"
        )

        destination = (
            self.request.query_params.get(
                "destination_location"
            )
        )

        date_from = self.request.query_params.get(
            "date_from"
        )

        date_to = self.request.query_params.get(
            "date_to"
        )

        search = self.request.query_params.get(
            "search"
        )

        if item:
            queryset = queryset.filter(
                item_id=item
            )

        if source:
            queryset = queryset.filter(
                source_location_id=source
            )

        if destination:
            queryset = queryset.filter(
                destination_location_id=destination
            )

        if date_from:
            queryset = queryset.filter(
                created_at__date__gte=date_from
            )

        if date_to:
            queryset = queryset.filter(
                created_at__date__lte=date_to
            )

        if search:
            queryset = queryset.filter(
                Q(reference__icontains=search)
                | Q(notes__icontains=search)
                | Q(
                    item__item_code__icontains=search
                )
                | Q(
                    item__name__icontains=search
                )
            )

        return queryset

    # ========================================================
    # CREATE TRANSFER
    # ========================================================

    def perform_create(self, serializer):

        requested_item = (
            serializer.validated_data["item"]
        )

        quantity = (
            serializer.validated_data["quantity"]
        )

        source_location = (
            serializer.validated_data[
                "source_location"
            ]
        )

        destination_location = (
            serializer.validated_data[
                "destination_location"
            ]
        )

        # ----------------------------------------------------
        # SOURCE AND DESTINATION MUST DIFFER
        # ----------------------------------------------------

        if (
            source_location.pk
            == destination_location.pk
        ):

            raise ValidationError(
                {
                    "destination_location": (
                        "Source and destination "
                        "locations must be different."
                    )
                }
            )

        with transaction.atomic():

            # ------------------------------------------------
            # LOCK ITEM
            # ------------------------------------------------

            locked_item = (
                Item.objects
                .select_for_update()
                .get(
                    pk=requested_item.pk
                )
            )

            # ------------------------------------------------
            # ACTIVE ITEM CHECK
            # ------------------------------------------------

            if not locked_item.is_active:

                raise ValidationError(
                    {
                        "item": (
                            "Stock cannot be transferred "
                            "for an inactive item."
                        )
                    }
                )

            # ------------------------------------------------
            # CALCULATE SOURCE LOCATION STOCK
            # ------------------------------------------------

            source_stock = (
                StockTransaction.objects
                .filter(
                    item=locked_item,
                    location=source_location,
                )
                .aggregate(
                    total=Sum(
                        Case(
                            When(
                                transaction_type__in=[
                                    StockTransaction
                                    .TransactionType
                                    .RECEIVED,

                                    StockTransaction
                                    .TransactionType
                                    .RETURNED,
                                ],
                                then="quantity",
                            ),

                            When(
                                transaction_type=(
                                    StockTransaction
                                    .TransactionType
                                    .ISSUED
                                ),
                                then=-F("quantity"),
                            ),

                            When(
                                transaction_type=(
                                    StockTransaction
                                    .TransactionType
                                    .ADJUSTMENT
                                ),
                                then="quantity",
                            ),

                            default=0,

                            output_field=IntegerField(),
                        )
                    )
                )["total"] or 0
            )

            # ------------------------------------------------
            # INSUFFICIENT SOURCE STOCK
            # ------------------------------------------------

            if quantity > source_stock:

                raise ValidationError(
                    {
                        "quantity": (
                            "Insufficient stock at the "
                            "source location. "
                            f"Available stock is "
                            f"{source_stock}."
                        )
                    }
                )

            # ------------------------------------------------
            # CREATE TRANSFER
            # ------------------------------------------------

            transfer = serializer.save(
                item=locked_item,
                transferred_by=self.request.user,
                status=(
                    StockTransfer
                    .Status
                    .COMPLETED
                ),
            )

            # ------------------------------------------------
            # SOURCE ISSUE
            # ------------------------------------------------

            StockTransaction.objects.create(
                item=locked_item,

                transaction_type=(
                    StockTransaction
                    .TransactionType
                    .ISSUED
                ),

                quantity=quantity,

                reference=transfer.reference,

                notes=(
                    "Stock transferred to "
                    f"{destination_location.name}."
                ),

                location=source_location,

                created_by=self.request.user,
            )

            # ------------------------------------------------
            # DESTINATION RECEIPT
            # ------------------------------------------------

            StockTransaction.objects.create(
                item=locked_item,

                transaction_type=(
                    StockTransaction
                    .TransactionType
                    .RECEIVED
                ),

                quantity=quantity,

                reference=transfer.reference,

                notes=(
                    "Stock transferred from "
                    f"{source_location.name}."
                ),

                location=destination_location,

                created_by=self.request.user,
            )