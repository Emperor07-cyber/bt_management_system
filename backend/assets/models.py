from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models
from django.db.models import Q
from django.utils import timezone


class AssetCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "asset_categories"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["is_active", "name"]),
        ]

    def __str__(self):
        return self.name


class Asset(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        ASSIGNED = "ASSIGNED", "Assigned"
        MAINTENANCE = "MAINTENANCE", "Maintenance"
        RETIRED = "RETIRED", "Retired"

    class Condition(models.TextChoices):
        NEW = "NEW", "New"
        EXCELLENT = "EXCELLENT", "Excellent"
        GOOD = "GOOD", "Good"
        FAIR = "FAIR", "Fair"
        POOR = "POOR", "Poor"
        DAMAGED = "DAMAGED", "Damaged"

    name = models.CharField(max_length=150)
    asset_code = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    manufacturer = models.CharField(max_length=150, blank=True)
    model_number = models.CharField(max_length=150, blank=True)
    serial_number = models.CharField(max_length=150, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    purchase_cost = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    warranty_start = models.DateField(null=True, blank=True)
    warranty_end = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    # Condition remains part of the asset's current state, but is deliberately
    # not requested during initial asset registration in the UI. It is managed
    # through maintenance/condition workflows.
    condition = models.CharField(max_length=20, choices=Condition.choices, default=Condition.GOOD)
    location = models.ForeignKey("company.Location", on_delete=models.SET_NULL, null=True, blank=True, related_name="assets")
    # Kept for backward compatibility with existing records and reports.
    # New assignments must go through AssetAssignment; this field is maintained
    # by the assignment workflow and is read-only through AssetSerializer.
    employee = models.ForeignKey("company.Employee", on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_assets")
    supplier = models.ForeignKey("company.Supplier", on_delete=models.SET_NULL, null=True, blank=True, related_name="assets")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assets"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["asset_code"]),
            models.Index(fields=["category"]),
            models.Index(fields=["status"]),
            models.Index(fields=["condition"]),
            models.Index(fields=["purchase_date"]),
            models.Index(fields=["location"]),
            models.Index(fields=["employee"]),
            models.Index(fields=["supplier"]),
            models.Index(fields=["created_at"]),
        ]

    def clean(self):
        errors = {}
        if self.purchase_cost is not None and self.purchase_cost < 0:
            errors["purchase_cost"] = "Purchase cost cannot be negative."
        if self.warranty_start and self.warranty_end and self.warranty_end < self.warranty_start:
            errors["warranty_end"] = "Warranty end date cannot be earlier than warranty start date."
        if self.status == self.Status.ASSIGNED and self.employee is None:
            errors["employee"] = "An assigned asset must have an active assignment."
        if self.employee is not None and self.employee.status != "ACTIVE":
            errors["employee"] = "An asset can only be assigned to an active employee."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # Asset codes are system-generated. New assets receive the next
        # BT-XXXXXX code; existing codes are preserved for compatibility.
        if not self.asset_code:
            from django.db.models.functions import Cast
            from django.db.models import IntegerField
            from django.db.models.functions import Substr

            for _ in range(5):
                last_code = (
                    type(self).objects
                    .filter(asset_code__regex=r"^BT-[0-9]+$")
                    .annotate(code_number=Cast(
                        Substr("asset_code", 4),
                        IntegerField(),
                    ))
                    .order_by("-code_number")
                    .values_list("code_number", flat=True)
                    .first()
                )
                next_number = (last_code or 0) + 1
                self.asset_code = f"BT-{next_number:06d}"
                try:
                    return super().save(*args, **kwargs)
                except IntegrityError:
                    # Another request may have generated the same code.
                    # Retry with the next available sequence number.
                    self.asset_code = ""
            raise IntegrityError("Unable to generate a unique asset code after multiple attempts.")

        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.asset_code} - {self.name}"


class AssetAssignment(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        RETURNED = "RETURNED", "Returned"
        CANCELLED = "CANCELLED", "Cancelled"

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="assignments")
    employee = models.ForeignKey("company.Employee", on_delete=models.PROTECT, related_name="asset_assignments")
    assignment_date = models.DateField(default=timezone.localdate)
    expected_return_date = models.DateField(null=True, blank=True)
    return_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="asset_assignments_created")
    returned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="asset_assignments_returned")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "asset_assignments"
        ordering = ["-assignment_date", "-created_at"]
        indexes = [
            models.Index(fields=["asset", "status"]),
            models.Index(fields=["employee", "status"]),
            models.Index(fields=["assignment_date"]),
            models.Index(fields=["return_date"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["asset"],
                condition=Q(status="ACTIVE"),
                name="unique_active_asset_assignment",
            )
        ]

    def clean(self):
        errors = {}
        if self.employee_id and self.employee.status != "ACTIVE":
            errors["employee"] = "Only active employees can receive assets."
        if self.expected_return_date and self.expected_return_date < self.assignment_date:
            errors["expected_return_date"] = "Expected return date cannot be earlier than assignment date."
        if self.return_date and self.return_date < self.assignment_date:
            errors["return_date"] = "Return date cannot be earlier than assignment date."
        if self.status == self.Status.RETURNED and not self.return_date:
            errors["return_date"] = "A returned assignment must have a return date."
        if self.status == self.Status.ACTIVE and self.return_date:
            errors["return_date"] = "An active assignment cannot have a return date."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.asset.asset_code} - {self.employee} - {self.status}"


class AssetHistory(models.Model):
    class EventType(models.TextChoices):
        CREATED = "CREATED", "Created"
        UPDATED = "UPDATED", "Updated"
        ASSIGNED = "ASSIGNED", "Assigned"
        UNASSIGNED = "UNASSIGNED", "Unassigned"
        TRANSFERRED = "TRANSFERRED", "Transferred"
        STATUS_CHANGED = "STATUS_CHANGED", "Status Changed"
        CONDITION_CHANGED = "CONDITION_CHANGED", "Condition Changed"
        MAINTENANCE = "MAINTENANCE", "Maintenance"
        RETIRED = "RETIRED", "Retired"
        DISPOSED = "DISPOSED", "Disposed"

    asset = models.ForeignKey(Asset, on_delete=models.SET_NULL, null=True, blank=True, related_name="history")
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    event_date = models.DateTimeField(auto_now_add=True)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="asset_history_events")
    previous_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20, blank=True)
    previous_employee = models.ForeignKey("company.Employee", on_delete=models.SET_NULL, null=True, blank=True, related_name="asset_previous_assignments")
    new_employee = models.ForeignKey("company.Employee", on_delete=models.SET_NULL, null=True, blank=True, related_name="asset_new_assignments")
    previous_location = models.ForeignKey("company.Location", on_delete=models.SET_NULL, null=True, blank=True, related_name="asset_previous_locations")
    new_location = models.ForeignKey("company.Location", on_delete=models.SET_NULL, null=True, blank=True, related_name="asset_new_locations")
    description = models.TextField(blank=True)
    snapshot = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "asset_history"
        ordering = ["-event_date"]
        indexes = [
            models.Index(fields=["asset", "event_date"]),
            models.Index(fields=["event_type", "event_date"]),
            models.Index(fields=["performed_by"]),
        ]

    def __str__(self):
        asset_code = self.asset.asset_code if self.asset else self.snapshot.get("asset_code", "Deleted Asset")
        return f"{asset_code} - {self.event_type}"


class AssetMaintenance(models.Model):
    class MaintenanceType(models.TextChoices):
        SERVICE = "SERVICE", "Service"
        REPAIR = "REPAIR", "Repair"
        INSPECTION = "INSPECTION", "Inspection"
        CALIBRATION = "CALIBRATION", "Calibration"
        CLEANING = "CLEANING", "Cleaning"
        OTHER = "OTHER", "Other"

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="maintenance_records")
    maintenance_date = models.DateField()
    maintenance_type = models.CharField(max_length=30, choices=MaintenanceType.choices)
    description = models.TextField()
    service_provider = models.CharField(max_length=200, blank=True)
    cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    condition_before = models.CharField(max_length=20, choices=Asset.Condition.choices, blank=True)
    condition_after = models.CharField(max_length=20, choices=Asset.Condition.choices, blank=True)
    next_maintenance_date = models.DateField(null=True, blank=True)
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="asset_maintenance_records")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "asset_maintenance"
        ordering = ["-maintenance_date", "-created_at"]
        indexes = [
            models.Index(fields=["asset", "maintenance_date"]),
            models.Index(fields=["maintenance_type"]),
            models.Index(fields=["maintenance_date"]),
        ]

    def clean(self):
        if self.cost is not None and self.cost < 0:
            raise ValidationError({"cost": "Maintenance cost cannot be negative."})
        if self.next_maintenance_date and self.next_maintenance_date < self.maintenance_date:
            raise ValidationError({"next_maintenance_date": "Next maintenance date cannot be earlier than the maintenance date."})

    def __str__(self):
        return f"{self.asset.asset_code} - {self.maintenance_type} - {self.maintenance_date}"
