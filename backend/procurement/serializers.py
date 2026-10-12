from django.db import transaction
from django.db.models import Sum
from rest_framework import serializers

from .models import (
    PurchaseOrder,
    PurchaseOrderItem,
    GoodsReceipt,
    GoodsReceiptItem,
    SupplierInvoice,
    SupplierPayment,
)
from inventory.models import StockTransaction


class PurchaseOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrder
        fields = "__all__"

    def validate(self, attrs):
        order_date = attrs.get(
            "order_date",
            getattr(self.instance, "order_date", None),
        )
        expected_delivery_date = attrs.get(
            "expected_delivery_date",
            getattr(self.instance, "expected_delivery_date", None),
        )
        supplier = attrs.get(
            "supplier",
            getattr(self.instance, "supplier", None),
        )

        if (
            expected_delivery_date
            and order_date
            and expected_delivery_date < order_date
        ):
            raise serializers.ValidationError({
                "expected_delivery_date": (
                    "Expected delivery date cannot be before order date."
                )
            })

        if supplier is not None and not supplier.is_active:
            raise serializers.ValidationError({
                "supplier": "Purchase orders can only use active suppliers."
            })

        return attrs


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    total_price = serializers.ReadOnlyField()

    class Meta:
        model = PurchaseOrderItem
        fields = "__all__"

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Quantity must be greater than zero."
            )
        return value

    def validate_unit_price(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "Unit price cannot be negative."
            )
        return value


class GoodsReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoodsReceipt
        fields = "__all__"


class GoodsReceiptItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoodsReceiptItem
        fields = "__all__"

    def validate_quantity_received(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Quantity received must be greater than zero."
            )
        return value

    def validate(self, attrs):
        goods_receipt = attrs.get(
            "goods_receipt",
            getattr(self.instance, "goods_receipt", None),
        )
        item = attrs.get(
            "item",
            getattr(self.instance, "item", None),
        )
        quantity_received = attrs.get(
            "quantity_received",
            getattr(self.instance, "quantity_received", 0),
        )

        if goods_receipt is None or item is None:
            return attrs

        purchase_order = goods_receipt.purchase_order

        po_item = purchase_order.items.filter(item=item).first()

        if po_item is None:
            raise serializers.ValidationError({
                "item": (
                    "This item is not included in the related purchase order."
                )
            })

        received_query = GoodsReceiptItem.objects.filter(
            goods_receipt__purchase_order=purchase_order,
            item=item,
        )

        if self.instance:
            received_query = received_query.exclude(
                pk=self.instance.pk
            )

        already_received = (
            received_query.aggregate(
                total=Sum("quantity_received")
            )["total"] or 0
        )

        if already_received + quantity_received > po_item.quantity:
            raise serializers.ValidationError({
                "quantity_received": (
                    f"Cannot receive more than the ordered quantity "
                    f"({po_item.quantity}). "
                    f"Already received: {already_received}."
                )
            })

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        receipt_item = GoodsReceiptItem.objects.create(
            **validated_data
        )

        StockTransaction.objects.create(
            item=receipt_item.item,
            transaction_type=StockTransaction.TransactionType.RECEIVED,
            quantity=receipt_item.quantity_received,
            reference=receipt_item.goods_receipt.receipt_number,
            notes=(
                f"Goods received against "
                f"{receipt_item.goods_receipt.receipt_number}"
            ),
        )

        return receipt_item


class SupplierInvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierInvoice
        fields = "__all__"

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Invoice amount must be greater than zero."
            )
        return value

    def validate(self, attrs):
        invoice_date = attrs.get(
            "invoice_date",
            getattr(self.instance, "invoice_date", None),
        )
        due_date = attrs.get(
            "due_date",
            getattr(self.instance, "due_date", None),
        )
        supplier = attrs.get(
            "supplier",
            getattr(self.instance, "supplier", None),
        )
        purchase_order = attrs.get(
            "purchase_order",
            getattr(self.instance, "purchase_order", None),
        )

        if due_date and invoice_date and due_date < invoice_date:
            raise serializers.ValidationError({
                "due_date": "Due date cannot be before invoice date."
            })

        if supplier is not None and not supplier.is_active:
            raise serializers.ValidationError({
                "supplier": "Invoices can only use active suppliers."
            })

        if (
            purchase_order is not None
            and supplier is not None
            and purchase_order.supplier_id != supplier.id
        ):
            raise serializers.ValidationError({
                "supplier": (
                    "Invoice supplier must match the purchase order supplier."
                )
            })

        return attrs


class SupplierPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierPayment
        fields = "__all__"

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Payment amount must be greater than zero."
            )
        return value

    def validate(self, attrs):
        invoice = attrs.get(
            "invoice",
            getattr(self.instance, "invoice", None),
        )

        if invoice is None:
            return attrs

        if invoice.status == SupplierInvoice.Status.CANCELLED:
            raise serializers.ValidationError({
                "invoice": "Payments cannot be made against a cancelled invoice."
            })

        amount = attrs.get(
            "amount",
            getattr(self.instance, "amount", 0),
        )

        existing_paid = invoice.total_paid

        if self.instance:
            existing_paid -= self.instance.amount

        balance = invoice.amount - existing_paid

        if amount > balance:
            raise serializers.ValidationError({
                "amount": (
                    f"Payment cannot exceed the invoice balance "
                    f"({balance})."
                )
            })

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        invoice = (
            SupplierInvoice.objects
            .select_for_update()
            .get(pk=validated_data["invoice"].pk)
        )

        amount = validated_data["amount"]

        if invoice.status == SupplierInvoice.Status.CANCELLED:
            raise serializers.ValidationError({
                "invoice": "Payments cannot be made against a cancelled invoice."
            })

        if amount > invoice.balance:
            raise serializers.ValidationError({
                "amount": (
                    f"Payment cannot exceed the invoice balance "
                    f"({invoice.balance})."
                )
            })

        payment = SupplierPayment.objects.create(
            **validated_data
        )

        self._update_invoice_status(invoice)

        return payment

    @transaction.atomic
    def update(self, instance, validated_data):
        old_invoice = instance.invoice

        payment = super().update(instance, validated_data)

        invoices = {old_invoice.pk, payment.invoice_id}

        for invoice_id in invoices:
            invoice = (
                SupplierInvoice.objects
                .select_for_update()
                .get(pk=invoice_id)
            )
            self._update_invoice_status(invoice)

        return payment

    @staticmethod
    def _update_invoice_status(invoice):
        if invoice.status == SupplierInvoice.Status.CANCELLED:
            return

        if invoice.total_paid >= invoice.amount:
            invoice.status = SupplierInvoice.Status.PAID
        elif invoice.total_paid > 0:
            invoice.status = SupplierInvoice.Status.PARTIAL
        else:
            invoice.status = SupplierInvoice.Status.UNPAID

        invoice.save(update_fields=["status"])