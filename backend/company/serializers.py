from rest_framework import serializers

from .models import (
    CompanySetting,
    Department,
    Employee,
    EmployeeModuleAffiliation,
    Location,
    Supplier,
)


class DepartmentSerializer(serializers.ModelSerializer):
    manager_name = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]

    def get_manager_name(self, obj):
        if not obj.manager:
            return None

        return f"{obj.manager.first_name} {obj.manager.last_name}".strip()

    def validate(self, attrs):
        manager = attrs.get(
            "manager",
            getattr(self.instance, "manager", None),
        )

        if manager is not None:
            if manager.status != Employee.Status.ACTIVE:
                raise serializers.ValidationError({
                    "manager": (
                        "Department manager must be an active employee."
                    )
                })

            department_id = self.instance.id if self.instance else None

            if (
                department_id is not None
                and manager.department_id != department_id
            ):
                raise serializers.ValidationError({
                    "manager": (
                        "Department manager must belong to this department."
                    )
                })

        return attrs


class LocationSerializer(serializers.ModelSerializer):
    parent_name = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]

    def get_parent_name(self, obj):
        return obj.parent.name if obj.parent else None

    def validate(self, attrs):
        parent = attrs.get(
            "parent",
            getattr(self.instance, "parent", None),
        )

        if self.instance is not None and parent == self.instance:
            raise serializers.ValidationError({
                "parent": "A location cannot be its own parent."
            })

        if parent is not None and not parent.is_active:
            raise serializers.ValidationError({
                "parent": "A location cannot have an inactive parent."
            })

        if self.instance is not None and parent is not None:
            seen = {self.instance.pk}
            current = parent

            while current:
                if current.pk in seen:
                    raise serializers.ValidationError({
                        "parent": (
                            "Location hierarchy cannot contain a cycle."
                        )
                    })

                seen.add(current.pk)
                current = current.parent

        return attrs


class EmployeeSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    location_name = serializers.SerializerMethodField()
    active_affiliations = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()

    def get_department_name(self, obj):
        return obj.department.name if obj.department else None

    def get_location_name(self, obj):
        return obj.location.name if obj.location else None

    def get_active_affiliations(self, obj):
        return list(
            obj.module_affiliations.filter(
                is_active=True
            ).values_list(
                "module",
                flat=True,
            )
        )

    def validate(self, attrs):
        department = attrs.get(
            "department",
            getattr(self.instance, "department", None),
        )
        location = attrs.get(
            "location",
            getattr(self.instance, "location", None),
        )
        status = attrs.get(
            "status",
            getattr(
                self.instance,
                "status",
                Employee.Status.ACTIVE,
            ),
        )

        errors = {}

        if department is not None and not department.is_active:
            errors["department"] = (
                "Employee cannot be assigned to an inactive department."
            )

        if location is not None and not location.is_active:
            errors["location"] = (
                "Employee cannot be assigned to an inactive location."
            )

        if status == Employee.Status.INACTIVE and self.instance is not None:
            # Active affiliations are automatically deactivated in the view.
            pass

        if errors:
            raise serializers.ValidationError(errors)

        return attrs


class EmployeeModuleAffiliationSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    module_label = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeModuleAffiliation
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]

    def get_employee_name(self, obj):
        return f"{obj.employee.first_name} {obj.employee.last_name}".strip()

    def get_module_label(self, obj):
        return obj.get_module_display()

    def validate(self, attrs):
        employee = attrs.get(
            "employee",
            getattr(self.instance, "employee", None),
        )
        is_active = attrs.get(
            "is_active",
            getattr(self.instance, "is_active", True),
        )

        if (
            employee is not None
            and is_active
            and employee.status != Employee.Status.ACTIVE
        ):
            raise serializers.ValidationError({
                "employee": (
                    "Only active employees can have an active "
                    "module affiliation."
                )
            })

        return attrs


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, attrs):
        name = attrs.get(
            "name",
            getattr(self.instance, "name", ""),
        )

        if not name or not name.strip():
            raise serializers.ValidationError({
                "name": "Supplier name cannot be blank."
            })

        return attrs


class CompanySettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanySetting
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]

    def validate_currency_code(self, value):
        value = value.strip().upper()

        if len(value) != 3:
            raise serializers.ValidationError(
                "Currency code must contain exactly 3 characters."
            )

        return value

    def validate(self, attrs):
        if self.instance is None and CompanySetting.objects.exists():
            raise serializers.ValidationError(
                "Only one company setting record is allowed."
            )

        return attrs