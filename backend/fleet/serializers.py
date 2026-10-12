from django.db import transaction
from rest_framework import serializers
from .models import Vehicle, VehicleAssignment, VehicleMaintenance


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = "__all__"


class VehicleAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleAssignment
        fields = "__all__"

    def validate(self, attrs):
        assignment_date = attrs.get(
            "assignment_date",
            getattr(self.instance, "assignment_date", None),
        )
        return_date = attrs.get(
            "return_date",
            getattr(self.instance, "return_date", None),
        )

        if return_date and assignment_date and return_date < assignment_date:
            raise serializers.ValidationError({
                "return_date": "Return date cannot be earlier than the assignment date."
            })

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        vehicle = Vehicle.objects.select_for_update().get(
            pk=validated_data["vehicle"].pk
        )
        assignment = VehicleAssignment.objects.create(**validated_data)

        vehicle.status = Vehicle.Status.ASSIGNED
        vehicle.save(update_fields=["status"])

        return assignment

    @transaction.atomic
    def update(self, instance, validated_data):
        old_vehicle_id = instance.vehicle_id
        assignment = super().update(instance, validated_data)

        vehicle_ids = {old_vehicle_id, assignment.vehicle_id}
        vehicles = Vehicle.objects.select_for_update().filter(id__in=vehicle_ids)

        for vehicle in vehicles:
            has_active_assignment = vehicle.assignments.filter(
                return_date__isnull=True
            ).exists()
            new_status = (
                Vehicle.Status.ASSIGNED
                if has_active_assignment
                else Vehicle.Status.AVAILABLE
            )

            if vehicle.status != new_status:
                vehicle.status = new_status
                vehicle.save(update_fields=["status"])

        return assignment


class VehicleMaintenanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleMaintenance
        fields = "__all__"

    def validate(self, attrs):
        maintenance_date = attrs.get(
            "maintenance_date",
            getattr(self.instance, "maintenance_date", None),
        )
        next_service_date = attrs.get(
            "next_service_date",
            getattr(self.instance, "next_service_date", None),
        )
        mileage = attrs.get(
            "mileage",
            getattr(self.instance, "mileage", None),
        )
        next_service_mileage = attrs.get(
            "next_service_mileage",
            getattr(self.instance, "next_service_mileage", None),
        )

        errors = {}

        if (
            next_service_date
            and maintenance_date
            and next_service_date < maintenance_date
        ):
            errors["next_service_date"] = (
                "Next service date cannot be earlier than the maintenance date."
            )

        if (
            next_service_mileage is not None
            and mileage is not None
            and next_service_mileage < mileage
        ):
            errors["next_service_mileage"] = (
                "Next service mileage cannot be lower than the current mileage."
            )

        if errors:
            raise serializers.ValidationError(errors)

        return attrs
