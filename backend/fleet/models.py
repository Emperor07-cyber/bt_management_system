from django.db import models  # type: ignore[reportMissingModuleSource]


class Vehicle(models.Model):
    class VehicleType(models.TextChoices):
        CAR = "CAR", "Car"
        VAN = "VAN", "Van"
        TRUCK = "TRUCK", "Truck"
        BUS = "BUS", "Bus"
        MOTORCYCLE = "MOTORCYCLE", "Motorcycle"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        ASSIGNED = "ASSIGNED", "Assigned"
        MAINTENANCE = "MAINTENANCE", "Maintenance"
        INACTIVE = "INACTIVE", "Inactive"
        DISPOSED = "DISPOSED", "Disposed"

    vehicle_code = models.CharField(max_length=50, unique=True)
    registration_number = models.CharField(max_length=50, unique=True)

    vehicle_type = models.CharField(
        max_length=20,
        choices=VehicleType.choices,
        default=VehicleType.CAR
    )

    make = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.PositiveIntegerField(null=True, blank=True)

    color = models.CharField(max_length=50, blank=True)
    vin = models.CharField(max_length=100, unique=True, null=True, blank=True)
    engine_number = models.CharField(max_length=100, unique=True, null=True, blank=True)

    purchase_date = models.DateField(null=True, blank=True)
    purchase_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE
    )

    current_mileage = models.PositiveIntegerField(default=0)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "fleet_vehicles"
        ordering = ["registration_number"]
        indexes = [
            models.Index(fields=["vehicle_code"]),
            models.Index(fields=["registration_number"]),
            models.Index(fields=["status"]),
            models.Index(fields=["vehicle_type"]),
        ]

    def __str__(self):
        return f"{self.registration_number} - {self.make} {self.model}"

class VehicleAssignment(models.Model):
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="assignments"
    )

    employee = models.ForeignKey(
        "company.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vehicle_assignments"
    )

    location = models.ForeignKey(
        "company.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vehicle_assignments"
    )

    assignment_date = models.DateField()
    return_date = models.DateField(null=True, blank=True)

    purpose = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "fleet_vehicle_assignments"
        ordering = ["-assignment_date"]
        indexes = [
            models.Index(fields=["vehicle"]),
            models.Index(fields=["employee"]),
            models.Index(fields=["location"]),
        ]
        constraints = [
            models.CheckConstraint(
    condition=models.Q(return_date__gte=models.F("assignment_date")),
    name="fleet_vehicle_assignment_return_date_after_assignment_date",
)
        ]

    def clean(self):
        super().clean()
        if self.return_date and self.assignment_date and self.return_date < self.assignment_date:
            raise models.ValidationError({
                "return_date": "Return date cannot be earlier than the assignment date."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        employee_label = str(self.employee) if self.employee else "Unassigned"
        return f"{self.vehicle} - {employee_label}"


class VehicleMaintenance(models.Model):
    class MaintenanceType(models.TextChoices):
        SERVICE = "SERVICE", "Service"
        REPAIR = "REPAIR", "Repair"
        INSPECTION = "INSPECTION", "Inspection"
        TYRE = "TYRE", "Tyre"
        OIL_CHANGE = "OIL_CHANGE", "Oil Change"
        OTHER = "OTHER", "Other"

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="maintenance_records"
    )

    maintenance_type = models.CharField(
        max_length=20,
        choices=MaintenanceType.choices,
        default=MaintenanceType.SERVICE
    )

    maintenance_date = models.DateField()
    mileage = models.PositiveIntegerField(default=0)
    description = models.TextField()
    service_provider = models.CharField(max_length=200, blank=True)

    cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    next_service_date = models.DateField(null=True, blank=True)
    next_service_mileage = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "fleet_vehicle_maintenance"
        ordering = ["-maintenance_date"]
        indexes = [
            models.Index(fields=["vehicle"]),
            models.Index(fields=["maintenance_date"]),
            models.Index(fields=["maintenance_type"]),
        ]
        constraints = [
            models.CheckConstraint(
    condition=models.Q(next_service_date__gte=models.F("maintenance_date"))
    | models.Q(next_service_date__isnull=True),
    name="fleet_vehicle_maintenance_next_service_date_after_maintenance_date",
),
            models.CheckConstraint(
                condition=models.Q(next_service_mileage__gte=models.F("mileage"))
                | models.Q(next_service_mileage__isnull=True),
                name="fleet_vehicle_maintenance_next_service_mileage_after_current_mileage",
            ),
        ]

    def clean(self):
        super().clean()
        if self.next_service_date and self.maintenance_date and self.next_service_date < self.maintenance_date:
            raise models.ValidationError({
                "next_service_date": "Next service date cannot be earlier than the maintenance date."
            })
        if self.next_service_mileage is not None and self.next_service_mileage < self.mileage:
            raise models.ValidationError({
                "next_service_mileage": "Next service mileage cannot be lower than the current mileage."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.vehicle} - {self.get_maintenance_type_display()}"
    