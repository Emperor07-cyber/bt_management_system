from datetime import date

from rest_framework.test import APITestCase

from authentication.models import Permission, Role, RolePermission, User, UserRole
from company.models import Employee, Location
from .models import Vehicle, VehicleAssignment, VehicleMaintenance


class FleetAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("fleet_test", password="pass1234")
        role = Role.objects.create(name="Fleet Test Role")
        for action in ("READ", "CREATE", "UPDATE", "DELETE"):
            permission = Permission.objects.create(permission_code=f"FLEET_{action}")
            RolePermission.objects.create(role=role, permission=permission)
        UserRole.objects.create(user=self.user, role=role)
        self.client.force_authenticate(self.user)

        self.location = Location.objects.create(
            location_code="LOC-FLT", name="Main Yard"
        )
        self.employee = Employee.objects.create(
            employee_number="EMP-FLT",
            first_name="Fleet",
            last_name="User",
        )
        self.vehicle = Vehicle.objects.create(
            vehicle_code="VH-001",
            registration_number="ABC-001",
            vehicle_type="CAR",
            make="Toyota",
            model="Corolla",
            current_mileage=10000,
        )

    def test_vehicle_crud(self):
        response = self.client.post(
            "/api/v1/fleet/vehicles/",
            {
                "vehicle_code": "VH-002",
                "registration_number": "ABC-002",
                "vehicle_type": "VAN",
                "make": "Ford",
                "model": "Transit",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        vehicle_id = response.data["id"]

        response = self.client.patch(
            f"/api/v1/fleet/vehicles/{vehicle_id}/",
            {"color": "White"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.delete(
            f"/api/v1/fleet/vehicles/{vehicle_id}/"
        )
        self.assertEqual(response.status_code, 204)

    def test_duplicate_vehicle_registration_is_rejected(self):
        response = self.client.post(
            "/api/v1/fleet/vehicles/",
            {
                "vehicle_code": "VH-002",
                "registration_number": "ABC-001",
                "vehicle_type": "CAR",
                "make": "Honda",
                "model": "Civic",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_assignment_sets_vehicle_assigned(self):
        response = self.client.post(
            "/api/v1/fleet/assignments/",
            {
                "vehicle": self.vehicle.id,
                "employee": self.employee.id,
                "location": self.location.id,
                "assignment_date": "2026-09-10",
                "purpose": "Site visit",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, Vehicle.Status.ASSIGNED)

    def test_assignment_return_sets_vehicle_available(self):
        assignment = VehicleAssignment.objects.create(
            vehicle=self.vehicle,
            employee=self.employee,
            location=self.location,
            assignment_date=date(2026, 9, 1),
        )
        self.vehicle.status = Vehicle.Status.ASSIGNED
        self.vehicle.save(update_fields=["status"])

        response = self.client.patch(
            f"/api/v1/fleet/assignments/{assignment.id}/",
            {"return_date": "2026-09-10"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, Vehicle.Status.AVAILABLE)

    def test_vehicle_remains_assigned_when_another_active_assignment_exists(self):
        first = VehicleAssignment.objects.create(
            vehicle=self.vehicle,
            employee=self.employee,
            location=self.location,
            assignment_date=date(2026, 9, 1),
        )
        second = VehicleAssignment.objects.create(
            vehicle=self.vehicle,
            employee=self.employee,
            location=self.location,
            assignment_date=date(2026, 9, 5),
        )
        self.vehicle.status = Vehicle.Status.ASSIGNED
        self.vehicle.save(update_fields=["status"])

        response = self.client.patch(
            f"/api/v1/fleet/assignments/{first.id}/",
            {"return_date": "2026-09-10"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, Vehicle.Status.ASSIGNED)
        self.assertIsNone(second.return_date)

    def test_invalid_assignment_return_date_is_rejected(self):
        response = self.client.post(
            "/api/v1/fleet/assignments/",
            {
                "vehicle": self.vehicle.id,
                "employee": self.employee.id,
                "assignment_date": "2026-09-10",
                "return_date": "2026-09-09",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("return_date", response.data)

    def test_maintenance_list_and_create(self):
        response = self.client.post(
            "/api/v1/fleet/maintenance/",
            {
                "vehicle": self.vehicle.id,
                "maintenance_type": "SERVICE",
                "maintenance_date": "2026-09-10",
                "mileage": 10000,
                "description": "Routine service",
                "cost": "125000.00",
                "next_service_date": "2027-03-10",
                "next_service_mileage": 15000,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["vehicle"], self.vehicle.id)

        response = self.client.get("/api/v1/fleet/maintenance/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_maintenance_invalid_next_service_date_is_rejected(self):
        response = self.client.post(
            "/api/v1/fleet/maintenance/",
            {
                "vehicle": self.vehicle.id,
                "maintenance_type": "SERVICE",
                "maintenance_date": "2026-09-10",
                "mileage": 10000,
                "description": "Routine service",
                "cost": "50000.00",
                "next_service_date": "2026-09-09",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("next_service_date", response.data)

    def test_maintenance_invalid_next_service_mileage_is_rejected(self):
        response = self.client.post(
            "/api/v1/fleet/maintenance/",
            {
                "vehicle": self.vehicle.id,
                "maintenance_type": "SERVICE",
                "maintenance_date": "2026-09-10",
                "mileage": 10000,
                "description": "Routine service",
                "cost": "50000.00",
                "next_service_mileage": 9000,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("next_service_mileage", response.data)

    def test_fleet_list_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/v1/fleet/vehicles/")
        self.assertIn(response.status_code, (401, 403))
