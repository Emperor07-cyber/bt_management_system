
from django.conf import settings
from django.db import models


class ImportBatch(models.Model):
    class Module(models.TextChoices):
        ASSETS = "ASSETS", "Assets"
        INVENTORY = "INVENTORY", "Inventory"
        FLEET = "FLEET", "Fleet"
        PROCUREMENT = "PROCUREMENT", "Procurement"
        FINANCE = "FINANCE", "Finance"
        COMPANY = "COMPANY", "Company"

    class Status(models.TextChoices):
        UPLOADED = "UPLOADED", "Uploaded"
        VALIDATING = "VALIDATING", "Validating"
        VALIDATED = "VALIDATED", "Validated"
        IMPORTING = "IMPORTING", "Importing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    module = models.CharField(
        max_length=30,
        choices=Module.choices,
    )

    import_type = models.CharField(
        max_length=50,
    )

    file_name = models.CharField(
        max_length=255,
    )
    file = models.FileField(
    upload_to="imports/%Y/%m/%d/",
    null=True,
    blank=True,
    )

    file_path = models.CharField(
        max_length=500,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UPLOADED,
    )
    

    total_rows = models.PositiveIntegerField(default=0)
    valid_rows = models.PositiveIntegerField(default=0)
    invalid_rows = models.PositiveIntegerField(default=0)
    imported_rows = models.PositiveIntegerField(default=0)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="import_batches",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "import_batches"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["module"]),
            models.Index(fields=["import_type"]),
            models.Index(fields=["status"]),
            models.Index(fields=["uploaded_by"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return (
            f"{self.module} - "
            f"{self.import_type} - "
            f"{self.file_name}"
        )


class ImportError(models.Model):
    batch = models.ForeignKey(
        ImportBatch,
        on_delete=models.CASCADE,
        related_name="errors",
    )

    row_number = models.PositiveIntegerField()

    column_name = models.CharField(
        max_length=100,
        blank=True,
    )

    error_code = models.CharField(
        max_length=100,
    )

    message = models.TextField()

    row_data = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "import_errors"
        ordering = ["row_number", "id"]
        indexes = [
            models.Index(fields=["batch"]),
            models.Index(fields=["row_number"]),
            models.Index(fields=["error_code"]),
        ]

    def __str__(self):
        return (
            f"Batch {self.batch_id} - "
            f"Row {self.row_number}: "
            f"{self.message}"
        )
