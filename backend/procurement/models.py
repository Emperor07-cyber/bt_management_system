from django.db import models


class PurchaseOrder(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        ORDERED = "ORDERED", "Ordered"
        RECEIVED = "RECEIVED", "Received"
        CANCELLED = "CANCELLED", "Cancelled"

    order_number = models.CharField(max_length=50, unique=True)

    supplier = models.ForeignKey(
        "company.Supplier",
        on_delete=models.PROTECT,
        related_name="purchase_orders"
    )

    order_date = models.DateField()

    expected_delivery_date = models.DateField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "procurement_purchase_orders"
        ordering = ["-order_date"]
        indexes = [
            models.Index(fields=["order_number"]),
            models.Index(fields=["supplier"]),
            models.Index(fields=["status"]),
            models.Index(fields=["order_date"]),
        ]

    def __str__(self):
        return self.order_number


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="items"
    )

    item = models.ForeignKey(
        "inventory.Item",
        on_delete=models.PROTECT,
        related_name="purchase_order_items"
    )

    quantity = models.PositiveIntegerField()

    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_price(self):
        return self.quantity * self.unit_price

    class Meta:
        db_table = "procurement_purchase_order_items"
        ordering = ["id"]
        indexes = [
            models.Index(fields=["purchase_order"]),
            models.Index(fields=["item"]),
        ]

    def __str__(self):
        return f"{self.purchase_order} - {self.item}"
class GoodsReceipt(models.Model):
    class Status(models.TextChoices):
        RECEIVED = "RECEIVED", "Received"
        PARTIAL = "PARTIAL", "Partial"
        CANCELLED = "CANCELLED", "Cancelled"

    receipt_number = models.CharField(max_length=50, unique=True)

    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.PROTECT,
        related_name="goods_receipts"
    )

    receipt_date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RECEIVED
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "procurement_goods_receipts"
        ordering = ["-receipt_date"]

    def __str__(self):
        return self.receipt_number


class GoodsReceiptItem(models.Model):
    goods_receipt = models.ForeignKey(
        GoodsReceipt,
        on_delete=models.CASCADE,
        related_name="items"
    )

    item = models.ForeignKey(
        "inventory.Item",
        on_delete=models.PROTECT,
        related_name="goods_receipt_items"
    )

    quantity_received = models.PositiveIntegerField()

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "procurement_goods_receipt_items"
        ordering = ["id"]

    def __str__(self):
        return f"{self.goods_receipt} - {self.item}"
class SupplierInvoice(models.Model):
    class Status(models.TextChoices):
        UNPAID = "UNPAID", "Unpaid"
        PARTIAL = "PARTIAL", "Partially Paid"
        PAID = "PAID", "Paid"
        CANCELLED = "CANCELLED", "Cancelled"

    invoice_number = models.CharField(max_length=100, unique=True)

    supplier = models.ForeignKey(
        "company.Supplier",
        on_delete=models.PROTECT,
        related_name="invoices"
    )

    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.PROTECT,
        related_name="invoices",
        null=True,
        blank=True
    )

    invoice_date = models.DateField()

    due_date = models.DateField(
        null=True,
        blank=True
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UNPAID
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_paid(self):
        return self.payments.aggregate(
            total=models.Sum("amount")
        )["total"] or 0

    @property
    def balance(self):
        return self.amount - self.total_paid

    class Meta:
        db_table = "procurement_supplier_invoices"
        ordering = ["-invoice_date"]
        indexes = [
            models.Index(fields=["invoice_number"]),
            models.Index(fields=["supplier"]),
            models.Index(fields=["status"]),
            models.Index(fields=["invoice_date"]),
        ]

    def __str__(self):
        return self.invoice_number


class SupplierPayment(models.Model):
    class PaymentMethod(models.TextChoices):
        CASH = "CASH", "Cash"
        BANK_TRANSFER = "BANK_TRANSFER", "Bank Transfer"
        CARD = "CARD", "Card"
        OTHER = "OTHER", "Other"

    invoice = models.ForeignKey(
        SupplierInvoice,
        on_delete=models.PROTECT,
        related_name="payments"
    )

    payment_date = models.DateField()

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.BANK_TRANSFER
    )

    reference = models.CharField(
        max_length=100,
        blank=True
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "procurement_supplier_payments"
        ordering = ["-payment_date"]
        indexes = [
            models.Index(fields=["invoice"]),
            models.Index(fields=["payment_date"]),
            models.Index(fields=["payment_method"]),
        ]

    def __str__(self):
        return f"{self.invoice} - {self.amount}"