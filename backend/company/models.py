from django.core.exceptions import ValidationError
from django.db import models


class Department(models.Model):
    department_code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    manager = models.ForeignKey(
        "Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_departments",
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "departments"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["is_active"]),
        ]

    def clean(self):
        if self.manager_id:
            if self.manager.status != Employee.Status.ACTIVE:
                raise ValidationError({
                    "manager": (
                        "Department manager must be an active employee."
                    )
                })

            if self.manager.department_id != self.id:
                raise ValidationError({
                    "manager": (
                        "Department manager must belong to this department."
                    )
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.department_code} - {self.name}"


class Location(models.Model):
    name = models.CharField(max_length=150)
    address = models.TextField(blank=True)

    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "locations"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["parent"]),
            models.Index(fields=["is_active"]),
        ]

    def clean(self):
        # A new Location has no primary key yet, so do not compare
        # None == None and incorrectly treat it as self-parented.
        if self.pk and self.parent_id == self.pk:
            raise ValidationError({
                "parent": "A location cannot be its own parent."
            })

        if self.parent and not self.parent.is_active:
            raise ValidationError({
                "parent": "A location cannot have an inactive parent."
            })

        # Prevent deeper circular parent chains.
        seen = {self.pk} if self.pk else set()
        parent = self.parent

        while parent is not None:
            if parent.pk in seen:
                raise ValidationError({
                    "parent": "Location hierarchy cannot contain a cycle."
                })

            seen.add(parent.pk)
            parent = parent.parent

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Employee(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"

    employee_number = models.CharField(max_length=30, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
    )

    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "employees"
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(fields=["department"]),
            models.Index(fields=["location"]),
            models.Index(fields=["status"]),
            models.Index(fields=["employee_number"]),
        ]

    def clean(self):
        if self.department_id and not self.department.is_active:
            raise ValidationError({
                "department": (
                    "Employee cannot be assigned to an inactive department."
                )
            })

        if self.location_id and not self.location.is_active:
            raise ValidationError({
                "location": (
                    "Employee cannot be assigned to an inactive location."
                )
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee_number} - {self.first_name} {self.last_name}"


class Supplier(models.Model):
    supplier_code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    tax_number = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "suppliers"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["is_active"]),
        ]

    def clean(self):
        if not self.name or not self.name.strip():
            raise ValidationError({
                "name": "Supplier name cannot be blank."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.supplier_code} - {self.name}"


class CompanySetting(models.Model):
    company_name = models.CharField(max_length=200)
    company_code = models.CharField(max_length=50, unique=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    logo_path = models.CharField(max_length=500, blank=True)

    currency_code = models.CharField(max_length=3, default="NGN")
    timezone = models.CharField(max_length=100, default="Africa/Lagos")
    fiscal_year_start = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "company_settings"
        ordering = ["id"]

    def clean(self):
        if not self.company_name or not self.company_name.strip():
            raise ValidationError({
                "company_name": "Company name cannot be blank."
            })

        if self.currency_code:
            self.currency_code = self.currency_code.strip().upper()

            if len(self.currency_code) != 3:
                raise ValidationError({
                    "currency_code": (
                        "Currency code must contain exactly 3 characters."
                    )
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.company_name


class EmployeeModuleAffiliation(models.Model):
    class Module(models.TextChoices):
        INVENTORY = "INVENTORY", "Inventory"
        FLEET = "FLEET", "Fleet"
        ASSETS = "ASSETS", "Assets"
        PROCUREMENT = "PROCUREMENT", "Procurement"
        FINANCE = "FINANCE", "Finance"

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="module_affiliations",
    )

    module = models.CharField(
        max_length=30,
        choices=Module.choices,
    )

    function = models.CharField(
        max_length=100,
        blank=True,
        help_text="Operational function within the module.",
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "employee_module_affiliations"
        ordering = ["module", "employee"]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "module"],
                name="unique_employee_module_affiliation",
            )
        ]
        indexes = [
            models.Index(fields=["module"]),
            models.Index(fields=["employee"]),
            models.Index(fields=["is_active"]),
        ]

    def clean(self):
        if (
            self.is_active
            and self.employee.status != Employee.Status.ACTIVE
        ):
            raise ValidationError({
                "employee": (
                    "Only active employees can have an active "
                    "module affiliation."
                )
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        if self.function:
            return f"{self.employee} - {self.module} - {self.function}"

        return f"{self.employee} - {self.module}"