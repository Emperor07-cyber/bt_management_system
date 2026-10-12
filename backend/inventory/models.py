import re

from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "inventory_categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Item(models.Model):

    class Unit(models.TextChoices):
        PIECE = "PIECE", "Piece"
        BOX = "BOX", "Box"
        PACK = "PACK", "Pack"
        SET = "SET", "Set"
        LITRE = "LITRE", "Litre"
        KILOGRAM = "KG", "Kilogram"
        METER = "METER", "Meter"

    item_code = models.CharField(max_length=50, unique=True)

    @classmethod
    def _generate_next_item_code(cls):
        max_number = 0
        existing_codes = cls.objects.filter(
            item_code__startswith="BT-"
        ).values_list("item_code", flat=True)

        for code in existing_codes:
            match = re.fullmatch(r"BT-(\d+)", str(code))
            if match:
                max_number = max(max_number, int(match.group(1)))

        return f"BT-{max_number + 1:06d}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            return super().save(*args, **kwargs)

        last_error = None
        for _ in range(10):
            self.item_code = self._generate_next_item_code()
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError as exc:
                last_error = exc

        if last_error is not None:
            raise last_error

        return super().save(*args, **kwargs)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="items",
    )

    brand = models.CharField(max_length=100, blank=True)
    model_number = models.CharField(max_length=150, blank=True)

    specifications = models.JSONField(default=dict, blank=True)

    supplier = models.ForeignKey(
        "company.Supplier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_items",
    )

    unit = models.CharField(
        max_length=20,
        choices=Unit.choices,
        default=Unit.PIECE,
    )

    reorder_level = models.PositiveIntegerField(default=0)
    minimum_stock = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def current_stock(self):
        received = self.stock_transactions.filter(
            transaction_type=StockTransaction.TransactionType.RECEIVED
        ).aggregate(total=models.Sum("quantity"))["total"] or 0

        returned = self.stock_transactions.filter(
            transaction_type=StockTransaction.TransactionType.RETURNED
        ).aggregate(total=models.Sum("quantity"))["total"] or 0

        issued = self.stock_transactions.filter(
            transaction_type=StockTransaction.TransactionType.ISSUED
        ).aggregate(total=models.Sum("quantity"))["total"] or 0

        adjusted = self.stock_transactions.filter(
            transaction_type=StockTransaction.TransactionType.ADJUSTMENT
        ).aggregate(total=models.Sum("quantity"))["total"] or 0

        return received + returned - issued + adjusted

    @property
    def stock_status(self):
        stock = self.current_stock

        if stock <= self.minimum_stock:
            return "OUT_OF_STOCK"

        if stock <= self.reorder_level:
            return "LOW_STOCK"

        return "IN_STOCK"

    def __str__(self):
        return f"{self.item_code} - {self.name}"

    class Meta:
        db_table = "inventory_items"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["item_code"]),
            models.Index(fields=["category"]),
            models.Index(fields=["brand"]),
            models.Index(fields=["is_active"]),
        ]


class InventoryUnit(models.Model):

    class Condition(models.TextChoices):
        NEW = "NEW", "New"
        GOOD = "GOOD", "Good"
        FAIR = "FAIR", "Fair"
        DAMAGED = "DAMAGED", "Damaged"
        UNUSABLE = "UNUSABLE", "Unusable"

    class Status(models.TextChoices):
        IN_STOCK = "IN_STOCK", "In Stock"
        ASSIGNED = "ASSIGNED", "Assigned"
        MAINTENANCE = "MAINTENANCE", "Maintenance"
        LOST = "LOST", "Lost"
        DISPOSED = "DISPOSED", "Disposed"

    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        related_name="units",
    )

    asset_number = models.CharField(
        max_length=100,
        unique=True,
    )

    serial_number = models.CharField(
        max_length=150,
        unique=True,
        blank=True,
    )

    purchase_date = models.DateField(
        null=True,
        blank=True,
    )

    purchase_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    warranty_expiry = models.DateField(
        null=True,
        blank=True,
    )

    condition = models.CharField(
        max_length=20,
        choices=Condition.choices,
        default=Condition.NEW,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.IN_STOCK,
    )

    location = models.ForeignKey(
        "company.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_units",
    )

    assigned_to = models.ForeignKey(
        "company.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_inventory",
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.purchase_price is not None and self.purchase_price < 0:
            raise ValidationError(
                {"purchase_price": "Purchase price cannot be negative."}
            )

        if self.warranty_expiry and self.purchase_date:
            if self.warranty_expiry < self.purchase_date:
                raise ValidationError(
                    {
                        "warranty_expiry": (
                            "Warranty expiry cannot be before purchase date."
                        )
                    }
                )

        if self.status == self.Status.ASSIGNED:
            if self.assigned_to is None:
                raise ValidationError(
                    {
                        "assigned_to": (
                            "An employee is required when a unit is assigned."
                        )
                    }
                )

            if self.assigned_to.status != "ACTIVE":
                raise ValidationError(
                    {
                        "assigned_to": (
                            "Inventory can only be assigned to an active employee."
                        )
                    }
                )

        if self.status == self.Status.DISPOSED and self.assigned_to:
            raise ValidationError(
                {
                    "assigned_to": (
                        "A disposed inventory unit cannot be assigned."
                    )
                }
            )

        if self.status == self.Status.LOST and self.assigned_to:
            raise ValidationError(
                {
                    "assigned_to": (
                        "A lost inventory unit cannot be assigned."
                    )
                }
            )

    @staticmethod
    def _item_prefix(item_name):
        cleaned = re.sub(r"[^A-Za-z0-9]", "", str(item_name or "").upper())
        return cleaned[:3].ljust(3, "X")

    @classmethod
    def _generate_next_asset_number(cls, item):
        prefix = cls._item_prefix(item.name)
        pattern = re.compile(rf"BT-{re.escape(prefix)}-(\d+)$")
        max_number = 0

        existing_numbers = cls.objects.filter(
            asset_number__startswith=f"BT-{prefix}-"
        ).values_list("asset_number", flat=True)

        for asset_number in existing_numbers:
            match = pattern.fullmatch(str(asset_number))
            if match:
                max_number = max(max_number, int(match.group(1)))

        return f"BT-{prefix}-{max_number + 1:03d}"

    def save(self, *args, **kwargs):
        if self._state.adding:
            if self.item_id and self.item:
                self.asset_number = self._generate_next_asset_number(self.item)

        self.full_clean()
        return super().save(*args, **kwargs)

    class Meta:
        db_table = "inventory_units"
        ordering = ["asset_number"]
        indexes = [
            models.Index(fields=["item"]),
            models.Index(fields=["status"]),
            models.Index(fields=["location"]),
            models.Index(fields=["assigned_to"]),
            models.Index(fields=["serial_number"]),
        ]

    def __str__(self):
        return self.asset_number


class StockTransaction(models.Model):

    class TransactionType(models.TextChoices):
        RECEIVED = "RECEIVED", "Received"
        ISSUED = "ISSUED", "Issued"
        RETURNED = "RETURNED", "Returned"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"

    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        related_name="stock_transactions",
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
    )

    # Signed because ADJUSTMENT can legitimately be positive or negative.
    quantity = models.IntegerField()

    reference = models.CharField(
        max_length=100,
        blank=True,
    )

    notes = models.TextField(blank=True)

    employee = models.ForeignKey(
        "company.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_transactions",
    )

    location = models.ForeignKey(
        "company.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_transactions",
    )

    created_by = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_transactions_created",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.quantity == 0:
            raise ValidationError(
                {"quantity": "Quantity cannot be zero."}
            )

        if self.transaction_type in [
            self.TransactionType.RECEIVED,
            self.TransactionType.ISSUED,
            self.TransactionType.RETURNED,
        ] and self.quantity < 0:
            raise ValidationError(
                {
                    "quantity": (
                        "Received, issued, and returned quantities "
                        "must be positive."
                    )
                }
            )

        if self.transaction_type == self.TransactionType.ADJUSTMENT:
            if self.quantity == 0:
                raise ValidationError(
                    {
                        "quantity": (
                            "Adjustment quantity cannot be zero."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    class Meta:
        db_table = "stock_transactions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["item", "-created_at"]),
            models.Index(fields=["transaction_type"]),
            models.Index(fields=["location", "-created_at"]),
            models.Index(fields=["employee"]),
            models.Index(fields=["created_by"]),
        ]

    def __str__(self):
        return (
            f"{self.transaction_type} - "
            f"{self.item.name} - "
            f"{self.quantity}"
        )


class StockTransfer(models.Model):

    class Status(models.TextChoices):
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        related_name="stock_transfers",
    )

    quantity = models.PositiveIntegerField()

    source_location = models.ForeignKey(
        "company.Location",
        on_delete=models.PROTECT,
        related_name="outgoing_stock_transfers",
    )

    destination_location = models.ForeignKey(
        "company.Location",
        on_delete=models.PROTECT,
        related_name="incoming_stock_transfers",
    )

    reference = models.CharField(
        max_length=100,
        unique=True,
    )

    notes = models.TextField(blank=True)

    transferred_by = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_transfers_created",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.COMPLETED,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.quantity <= 0:
            raise ValidationError(
                {"quantity": "Transfer quantity must be greater than zero."}
            )

        if self.source_location_id == self.destination_location_id:
            raise ValidationError(
                {
                    "destination_location": (
                        "Source and destination locations "
                        "must be different."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    class Meta:
        db_table = "inventory_stock_transfers"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["item"]),
            models.Index(fields=["source_location"]),
            models.Index(fields=["destination_location"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.reference} - {self.item.name}"


class Stocktake(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    reference = models.CharField(max_length=100, unique=True)
    location = models.ForeignKey(
        "company.Location",
        on_delete=models.PROTECT,
        related_name="inventory_stocktakes",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        "authentication.User",
        on_delete=models.PROTECT,
        related_name="stocktakes_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stocktakes_completed",
    )

    class Meta:
        db_table = "inventory_stocktakes"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["location", "-created_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_by"]),
        ]

    def clean(self):
        if self.location_id and not self.location.is_active:
            raise ValidationError({"location": "Stocktake location must be active."})
        if self.status == self.Status.COMPLETED and not self.completed_at:
            raise ValidationError({"completed_at": "Completed stocktakes must have a completion time."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} - {self.location.name}"


class StocktakeLine(models.Model):
    stocktake = models.ForeignKey(
        Stocktake,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        related_name="stocktake_lines",
    )
    system_quantity = models.IntegerField(default=0)
    counted_quantity = models.PositiveIntegerField(null=True, blank=True)
    variance = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    counted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "inventory_stocktake_lines"
        ordering = ["item__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["stocktake", "item"],
                name="unique_stocktake_item",
            )
        ]
        indexes = [
            models.Index(fields=["stocktake"]),
            models.Index(fields=["item"]),
        ]

    def clean(self):
        if self.system_quantity < 0:
            raise ValidationError({"system_quantity": "System quantity cannot be negative."})
        if self.counted_quantity is not None:
            self.variance = self.counted_quantity - self.system_quantity

        if self.stocktake_id and self.stocktake.status == Stocktake.Status.COMPLETED:
            raise ValidationError("Completed stocktake lines cannot be changed.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.stocktake.reference} - {self.item.item_code}"


class InventoryUnitHistory(models.Model):

    class EventType(models.TextChoices):
        CREATED = "CREATED", "Created"
        UPDATED = "UPDATED", "Updated"
        ASSIGNED = "ASSIGNED", "Assigned"
        UNASSIGNED = "UNASSIGNED", "Unassigned"
        TRANSFERRED = "TRANSFERRED", "Transferred"
        STATUS_CHANGED = "STATUS_CHANGED", "Status Changed"
        CONDITION_CHANGED = "CONDITION_CHANGED", "Condition Changed"
        LOST = "LOST", "Lost"
        DISPOSED = "DISPOSED", "Disposed"

    unit = models.ForeignKey(
        InventoryUnit,
        on_delete=models.CASCADE,
        related_name="history",
    )

    event_type = models.CharField(
        max_length=30,
        choices=EventType.choices,
    )

    performed_by = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_unit_history",
    )

    previous_status = models.CharField(
        max_length=20,
        blank=True,
    )

    new_status = models.CharField(
        max_length=20,
        blank=True,
    )

    previous_condition = models.CharField(
        max_length=20,
        blank=True,
    )

    new_condition = models.CharField(
        max_length=20,
        blank=True,
    )

    previous_location = models.ForeignKey(
        "company.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    new_location = models.ForeignKey(
        "company.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    previous_employee = models.ForeignKey(
        "company.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    new_employee = models.ForeignKey(
        "company.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    description = models.TextField(blank=True)

    snapshot = models.JSONField(
        default=dict,
        blank=True,
    )

    event_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "inventory_unit_history"
        ordering = ["-event_date"]
        indexes = [
            models.Index(fields=["unit", "-event_date"]),
            models.Index(fields=["event_type"]),
            models.Index(fields=["performed_by"]),
        ]

    def __str__(self):
        return (
            f"{self.unit.asset_number} - "
            f"{self.event_type}"
        )