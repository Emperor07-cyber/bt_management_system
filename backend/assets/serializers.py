from rest_framework import serializers

from .models import Asset, AssetAssignment, AssetCategory, AssetHistory, AssetMaintenance


class AssetCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetCategory
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Category name is required.")
        return value


class AssetSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField(read_only=True)
    location_name = serializers.SerializerMethodField(read_only=True)
    supplier_name = serializers.SerializerMethodField(read_only=True)
    current_assignment_id = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Asset
        fields = "__all__"
        read_only_fields = ["asset_code", "employee", "employee_name", "current_assignment_id", "created_at", "updated_at"]

    def get_employee_name(self, obj):
        if not obj.employee:
            return None
        full_name = " ".join(part for part in [getattr(obj.employee, "first_name", ""), getattr(obj.employee, "last_name", "")] if part).strip()
        return full_name or getattr(obj.employee, "name", None) or getattr(obj.employee, "full_name", None) or getattr(obj.employee, "employee_number", None)

    def get_location_name(self, obj):
        if not obj.location:
            return None
        return getattr(obj.location, "name", None) or getattr(obj.location, "location_name", None) or getattr(obj.location, "location_code", None) or str(obj.location)

    def get_supplier_name(self, obj):
        if not obj.supplier:
            return None
        return getattr(obj.supplier, "name", None) or getattr(obj.supplier, "company_name", None) or getattr(obj.supplier, "supplier_name", None) or str(obj.supplier)

    def get_current_assignment_id(self, obj):
        assignment = obj.assignments.filter(status=AssetAssignment.Status.ACTIVE).only("id").first()
        return assignment.id if assignment else None

    def validate_purchase_cost(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Purchase cost cannot be negative.")
        return value

    def validate(self, attrs):
        warranty_start = attrs.get("warranty_start", getattr(self.instance, "warranty_start", None))
        warranty_end = attrs.get("warranty_end", getattr(self.instance, "warranty_end", None))
        status = attrs.get("status", getattr(self.instance, "status", Asset.Status.AVAILABLE))
        if warranty_start and warranty_end and warranty_end < warranty_start:
            raise serializers.ValidationError({"warranty_end": "Warranty end date cannot be earlier than warranty start date."})
        if status == Asset.Status.ASSIGNED:
            raise serializers.ValidationError({"status": "Use Asset Assignment to assign an asset. Do not set Assigned status manually."})
        return attrs


class AssetAssignmentSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField(read_only=True)
    asset_code = serializers.CharField(source="asset.asset_code", read_only=True)
    asset_name = serializers.CharField(source="asset.name", read_only=True)
    location_name = serializers.CharField(source="asset.location.name", read_only=True, default=None)
    assigned_by_name = serializers.SerializerMethodField(read_only=True)
    returned_by_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AssetAssignment
        fields = "__all__"
        read_only_fields = ["status", "return_date", "assigned_by", "returned_by", "created_at", "updated_at", "employee_name", "asset_code", "asset_name", "location_name", "assigned_by_name", "returned_by_name"]

    def get_employee_name(self, obj):
        employee = obj.employee
        return " ".join(part for part in [employee.first_name, employee.last_name] if part).strip() or employee.employee_number

    def _user_name(self, user):
        if not user:
            return None
        return getattr(user, "username", None) or getattr(user, "email", None)

    def get_assigned_by_name(self, obj):
        return self._user_name(obj.assigned_by)

    def get_returned_by_name(self, obj):
        return self._user_name(obj.returned_by)

    def validate(self, attrs):
        asset = attrs.get("asset")
        employee = attrs.get("employee")
        assignment_date = attrs.get("assignment_date")
        expected_return_date = attrs.get("expected_return_date")
        if employee and employee.status != "ACTIVE":
            raise serializers.ValidationError({"employee": "Only active employees can receive assets."})
        if asset:
            if asset.status in [Asset.Status.RETIRED, Asset.Status.MAINTENANCE]:
                raise serializers.ValidationError({"asset": "A retired or maintenance asset cannot be assigned."})
            if asset.assignments.filter(status=AssetAssignment.Status.ACTIVE).exists():
                raise serializers.ValidationError({"asset": "This asset is already assigned."})
        if assignment_date and expected_return_date and expected_return_date < assignment_date:
            raise serializers.ValidationError({"expected_return_date": "Expected return date cannot be earlier than assignment date."})
        return attrs


class AssetHistorySerializer(serializers.ModelSerializer):
    asset_code = serializers.SerializerMethodField()
    asset_name = serializers.SerializerMethodField()

    class Meta:
        model = AssetHistory
        fields = "__all__"
        read_only_fields = ["event_date"]

    def get_asset_code(self, obj):
        return obj.asset.asset_code if obj.asset else obj.snapshot.get("asset_code")

    def get_asset_name(self, obj):
        return obj.asset.name if obj.asset else obj.snapshot.get("name")


class AssetMaintenanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetMaintenance
        fields = "__all__"
        read_only_fields = ["performed_by", "created_at", "updated_at"]

    def validate_cost(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Maintenance cost cannot be negative.")
        return value

    def validate(self, attrs):
        maintenance_date = attrs.get("maintenance_date")
        next_date = attrs.get("next_maintenance_date")
        if maintenance_date and next_date and next_date < maintenance_date:
            raise serializers.ValidationError({"next_maintenance_date": "Next maintenance date cannot be earlier than the maintenance date."})
        return attrs
