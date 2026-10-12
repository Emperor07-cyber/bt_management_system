from django.db import models
from rest_framework import serializers

from .models import (
    Category,
    Item,
    InventoryUnit,
    InventoryUnitHistory,
    StockTransaction,
    StockTransfer,
    Stocktake,
    StocktakeLine,
)


# ============================================================
# CATEGORY
# ============================================================

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


# ============================================================
# ITEM
# ============================================================

class ItemSerializer(serializers.ModelSerializer):
    current_stock = serializers.ReadOnlyField()
    stock_status = serializers.ReadOnlyField()

    class Meta:
        model = Item
        fields = [
            "id",
            "item_code",
            "name",
            "description",
            "category",
            "brand",
            "model_number",
            "specifications",
            "supplier",
            "unit",
            "reorder_level",
            "minimum_stock",
            "is_active",
            "created_at",
            "updated_at",
            "current_stock",
            "stock_status",
        ]
        read_only_fields = [
            "id",
            "item_code",
            "current_stock",
            "stock_status",
            "created_at",
            "updated_at",
        ]


# ============================================================
# INVENTORY UNIT
# ============================================================

class InventoryUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryUnit
        fields = "__all__"
        read_only_fields = [
            "id",
            "asset_number",
            "created_at",
            "updated_at",
        ]

    def validate_purchase_price(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError(
                "Purchase price cannot be negative."
            )
        return value

    def validate(self, attrs):
        instance = self.instance

        status = attrs.get(
            "status",
            instance.status if instance else InventoryUnit.Status.IN_STOCK,
        )

        assigned_to = attrs.get(
            "assigned_to",
            instance.assigned_to if instance else None,
        )

        purchase_date = attrs.get(
            "purchase_date",
            instance.purchase_date if instance else None,
        )

        warranty_expiry = attrs.get(
            "warranty_expiry",
            instance.warranty_expiry if instance else None,
        )

        # Assigned units must have an employee.
        if status == InventoryUnit.Status.ASSIGNED and assigned_to is None:
            raise serializers.ValidationError(
                {
                    "assigned_to": (
                        "An inventory unit with ASSIGNED status "
                        "must have an employee."
                    )
                }
            )

        # Lost/disposed units cannot remain assigned.
        if (
            status
            in [
                InventoryUnit.Status.LOST,
                InventoryUnit.Status.DISPOSED,
            ]
            and assigned_to is not None
        ):
            raise serializers.ValidationError(
                {
                    "assigned_to": (
                        "Lost or disposed inventory units "
                        "cannot be assigned to an employee."
                    )
                }
            )

        # Validate employee status.
        if assigned_to is not None:
            employee_status = getattr(assigned_to, "status", None)

            if employee_status is not None:
                status_value = str(employee_status).upper()

                if status_value not in ["ACTIVE"]:
                    raise serializers.ValidationError(
                        {
                            "assigned_to": (
                                "Inventory units can only be assigned "
                                "to active employees."
                            )
                        }
                    )

        # Warranty cannot expire before purchase.
        if (
            purchase_date is not None
            and warranty_expiry is not None
            and warranty_expiry < purchase_date
        ):
            raise serializers.ValidationError(
                {
                    "warranty_expiry": (
                        "Warranty expiry cannot be earlier "
                        "than the purchase date."
                    )
                }
            )

        return attrs


# ============================================================
# STOCK TRANSACTION
# ============================================================

class StockTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockTransaction
        fields = "__all__"
        read_only_fields = [
            "id",
            "created_by",
            "created_at",
        ]

    def validate_quantity(self, value):
        if value == 0:
            raise serializers.ValidationError(
                "Quantity cannot be zero."
            )

        return value

    def validate(self, attrs):
        transaction_type = attrs.get(
            "transaction_type",
            getattr(
                self.instance,
                "transaction_type",
                None,
            ),
        )

        quantity = attrs.get(
            "quantity",
            getattr(
                self.instance,
                "quantity",
                None,
            ),
        )

        item = attrs.get(
            "item",
            getattr(
                self.instance,
                "item",
                None,
            ),
        )

        location = attrs.get(
            "location",
            getattr(
                self.instance,
                "location",
                None,
            ),
        )

        if quantity is None:
            return attrs

        # RECEIVED, ISSUED and RETURNED must be positive.
        if transaction_type != StockTransaction.TransactionType.ADJUSTMENT:
            if quantity <= 0:
                raise serializers.ValidationError(
                    {
                        "quantity": (
                            "Quantity must be greater than zero "
                            "for RECEIVED, ISSUED and RETURNED transactions."
                        )
                    }
                )

        # ADJUSTMENT can be positive or negative, but not zero.
        if (
            transaction_type
            == StockTransaction.TransactionType.ADJUSTMENT
            and quantity == 0
        ):
            raise serializers.ValidationError(
                {
                    "quantity": (
                        "Adjustment quantity cannot be zero."
                    )
                }
            )

        # Prevent an issued quantity from exceeding global stock.
        if (
            transaction_type
            == StockTransaction.TransactionType.ISSUED
            and item is not None
        ):
            if quantity > item.current_stock:
                raise serializers.ValidationError(
                    {
                        "quantity": (
                            "Insufficient stock. "
                            f"Available stock is {item.current_stock}."
                        )
                    }
                )

        # Prevent negative adjustments from making stock negative.
        if (
            transaction_type
            == StockTransaction.TransactionType.ADJUSTMENT
            and quantity < 0
            and item is not None
        ):
            if location is not None:
                available_stock = (
                    StockTransaction.objects
                    .filter(
                        item=item,
                        location=location,
                    )
                    .aggregate(
                        total=models.Sum(
                            models.Case(
                                models.When(
                                    transaction_type__in=[
                                        StockTransaction.TransactionType.RECEIVED,
                                        StockTransaction.TransactionType.RETURNED,
                                    ],
                                    then="quantity",
                                ),
                                models.When(
                                    transaction_type=(
                                        StockTransaction.TransactionType.ISSUED
                                    ),
                                    then=models.F("quantity") * -1,
                                ),
                                models.When(
                                    transaction_type=(
                                        StockTransaction.TransactionType.ADJUSTMENT
                                    ),
                                    then="quantity",
                                ),
                                default=0,
                                output_field=models.IntegerField(),
                            )
                        )
                    )["total"]
                    or 0
                )
            else:
                available_stock = item.current_stock

            if abs(quantity) > available_stock:
                raise serializers.ValidationError(
                    {
                        "quantity": (
                            "Adjustment would make stock negative. "
                            f"Available stock is {available_stock}."
                        )
                    }
                )

        return attrs


# ============================================================
# STOCK TRANSFER
# ============================================================

class StockTransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockTransfer
        fields = "__all__"
        read_only_fields = [
            "id",
            "transferred_by",
            "status",
            "created_at",
        ]

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Transfer quantity must be greater than zero."
            )
        return value

    def validate(self, attrs):
        source_location = attrs.get(
            "source_location",
            getattr(
                self.instance,
                "source_location",
                None,
            ),
        )

        destination_location = attrs.get(
            "destination_location",
            getattr(
                self.instance,
                "destination_location",
                None,
            ),
        )

        if (
            source_location is not None
            and destination_location is not None
            and source_location.pk == destination_location.pk
        ):
            raise serializers.ValidationError(
                {
                    "destination_location": (
                        "Source and destination locations "
                        "must be different."
                    )
                }
            )

        return attrs


# ============================================================
# STOCKTAKING
# ============================================================

class StocktakeLineSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(
        source="item.name",
        read_only=True,
    )

    item_code = serializers.CharField(
        source="item.item_code",
        read_only=True,
    )

    location_stock = serializers.IntegerField(
        read_only=True,
    )

    class Meta:
        model = StocktakeLine
        fields = [
            "id",
            "stocktake",
            "item",
            "item_name",
            "item_code",
            "system_quantity",
            "counted_quantity",
            "variance",
            "location_stock",
            "notes",
            "counted_at",
        ]

        read_only_fields = [
            "id",
            "stocktake",
            "system_quantity",
            "variance",
            "location_stock",
            "counted_at",
        ]

    def validate_counted_quantity(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError(
                "Counted quantity cannot be negative."
            )

        return value


class StocktakeSerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(
        source="location.name",
        read_only=True,
    )

    created_by_name = serializers.SerializerMethodField()
    completed_by_name = serializers.SerializerMethodField()

    lines = StocktakeLineSerializer(
        many=True,
        read_only=True,
    )

    total_lines = serializers.SerializerMethodField()
    counted_lines = serializers.SerializerMethodField()
    variance_lines = serializers.SerializerMethodField()
    total_variance = serializers.SerializerMethodField()

    class Meta:
        model = Stocktake
        fields = [
            "id",
            "reference",
            "location",
            "location_name",
            "status",
            "notes",
            "created_by",
            "created_by_name",
            "created_at",
            "completed_at",
            "completed_by",
            "completed_by_name",
            "lines",
            "total_lines",
            "counted_lines",
            "variance_lines",
            "total_variance",
        ]

        read_only_fields = [
            "id",
            "created_by",
            "created_at",
            "completed_at",
            "completed_by",
            "lines",
            "total_lines",
            "counted_lines",
            "variance_lines",
            "total_variance",
        ]

    def get_created_by_name(self, obj):
        return getattr(
            obj.created_by,
            "username",
            None,
        )

    def get_completed_by_name(self, obj):
        return (
            getattr(
                obj.completed_by,
                "username",
                None,
            )
            if obj.completed_by
            else None
        )

    def get_total_lines(self, obj):
        return obj.lines.count()

    def get_counted_lines(self, obj):
        return obj.lines.filter(
            counted_quantity__isnull=False
        ).count()

    def get_variance_lines(self, obj):
        return obj.lines.exclude(
            variance=0
        ).count()

    def get_total_variance(self, obj):
        return sum(
            line.variance
            for line in obj.lines.all()
        )

    def validate(self, attrs):
        location = attrs.get(
            "location",
            getattr(
                self.instance,
                "location",
                None,
            ),
        )

        if location is not None and not location.is_active:
            raise serializers.ValidationError(
                {
                    "location": (
                        "Stocktake location must be active."
                    )
                }
            )

        if (
            self.instance
            and self.instance.status
            in [
                Stocktake.Status.COMPLETED,
                Stocktake.Status.CANCELLED,
            ]
        ):
            if any(
                key in attrs
                for key in [
                    "reference",
                    "location",
                ]
            ):
                raise serializers.ValidationError(
                    "Closed stocktakes cannot change "
                    "reference or location."
                )

        return attrs


# ============================================================
# INVENTORY UNIT HISTORY
# ============================================================

class InventoryUnitHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryUnitHistory
        fields = "__all__"
        read_only_fields = [
            "id",
            "event_date",
        ]