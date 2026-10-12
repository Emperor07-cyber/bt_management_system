from django.db import models


class ExpenseCategory(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
    )

    description = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "finance_expense_categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Expense(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        PAID = "PAID", "Paid"
        CANCELLED = "CANCELLED", "Cancelled"

    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name="expenses",
    )

    supplier = models.ForeignKey(
        "company.Supplier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
    )

    employee = models.ForeignKey(
        "company.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
    )

    location = models.ForeignKey(
        "company.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
    )

    expense_number = models.CharField(
        max_length=50,
        unique=True,
    )

    expense_date = models.DateField()

    description = models.TextField()

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    @property
    def total_paid(self):
        return (
            self.payments.aggregate(
                total=models.Sum("amount")
            )["total"]
            or 0
        )

    @property
    def balance(self):
        return self.amount - self.total_paid

    class Meta:
        db_table = "finance_expenses"
        ordering = ["-expense_date"]
        indexes = [
            models.Index(fields=["expense_number"]),
            models.Index(fields=["category"]),
            models.Index(fields=["supplier"]),
            models.Index(fields=["employee"]),
            models.Index(fields=["status"]),
            models.Index(fields=["expense_date"]),
        ]

    def __str__(self):
        return self.expense_number


class ExpensePayment(models.Model):
    class PaymentMethod(models.TextChoices):
        CASH = "CASH", "Cash"
        BANK_TRANSFER = "BANK_TRANSFER", "Bank Transfer"
        CARD = "CARD", "Card"
        OTHER = "OTHER", "Other"

    expense = models.ForeignKey(
        Expense,
        on_delete=models.PROTECT,
        related_name="payments",
    )

    payment_date = models.DateField()

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.BANK_TRANSFER,
    )

    reference = models.CharField(
        max_length=100,
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "finance_expense_payments"
        ordering = ["-payment_date"]
        indexes = [
            models.Index(fields=["expense"]),
            models.Index(fields=["payment_date"]),
            models.Index(fields=["payment_method"]),
        ]

    def __str__(self):
        return f"{self.expense} - {self.amount}"