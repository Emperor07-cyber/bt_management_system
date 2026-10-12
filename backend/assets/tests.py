"""Complete merged Asset API test suite: original coverage plus the dedicated AssetAssignment workflow."""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from datetime import date

from assets.models import Asset, AssetHistory, AssetMaintenance
from authentication.models import (
    Permission,
    Role,
    RolePermission,
    UserRole,
)
from company.models import Employee, Location


User = get_user_model()


class AssetAPITests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        # ---------------------------------------------------------
        # Test-only RBAC setup
        # ---------------------------------------------------------

        cls.admin_role = Role.objects.create(
            name="Admin",
            description="Test administrator role",
        )

        for action in ["CREATE", "READ", "UPDATE", "DELETE"]:
            permission = Permission.objects.create(
                permission_code=f"ASSET_{action}",
                description=f"Asset {action} permission",
            )

            RolePermission.objects.create(
                role=cls.admin_role,
                permission=permission,
            )

        cls.admin_user = User.objects.create_user(
            username="asset_test_admin",
            password="TestPass123!",
        )

        UserRole.objects.create(
            user=cls.admin_user,
            role=cls.admin_role,
        )

        # ---------------------------------------------------------
        # Location
        # ---------------------------------------------------------

        cls.location = Location.objects.create(
            location_code="LOC-TEST",
            name="Test Location",
        )

        # ---------------------------------------------------------
        # Active employee
        # ---------------------------------------------------------

        cls.employee = Employee.objects.create(
            employee_number="EMP-TEST-001",
            first_name="Test",
            last_name="Employee",
            email="employee@test.com",
            status=Employee.Status.ACTIVE,
            location=cls.location,
        )

        # ---------------------------------------------------------
        # Inactive employee
        # ---------------------------------------------------------

        cls.inactive_employee = Employee.objects.create(
            employee_number="EMP-TEST-002",
            first_name="Inactive",
            last_name="Employee",
            email="inactive@test.com",
            status=Employee.Status.INACTIVE,
            location=cls.location,
        )

    def setUp(self):
        self.client.force_authenticate(
            user=self.admin_user
        )

        # This dictionary is used for API requests.
        # DRF expects foreign-key IDs.
        self.asset_data = {
            "name": "Laptop",
            "asset_code": "AST-001",
            "category": "IT Equipment",
            "description": "Company laptop",
            "purchase_date": "2026-01-15",
            "purchase_cost": "150000.00",
            "status": Asset.Status.AVAILABLE,
            "location": self.location.id,
            "employee": None,
        }

    # =============================================================
    # CREATE
    # =============================================================

    def test_create_asset(self):
        response = self.client.post(
            "/api/v1/assets/",
            self.asset_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            Asset.objects.count(),
            1,
        )

        self.assertEqual(
            response.data["asset_code"],
            "AST-001",
        )

    # =============================================================
    # DUPLICATE CODE
    # =============================================================

    def test_duplicate_asset_code_rejected(self):
        Asset.objects.create(
            name="Existing Laptop",
            asset_code="AST-001",
            category="IT Equipment",
            description="Existing asset",
            purchase_date="2026-01-15",
            purchase_cost="150000.00",
            status=Asset.Status.AVAILABLE,
            location=self.location,
            employee=None,
        )

        response = self.client.post(
            "/api/v1/assets/",
            self.asset_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    # =============================================================
    # LIST
    # =============================================================

    def test_list_assets(self):
        Asset.objects.create(
            name="Existing Laptop",
            asset_code="AST-002",
            category="IT Equipment",
            description="Existing asset",
            purchase_date="2026-01-15",
            purchase_cost="150000.00",
            status=Asset.Status.AVAILABLE,
            location=self.location,
            employee=None,
        )

        response = self.client.get(
            "/api/v1/assets/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

    # =============================================================
    # RETRIEVE
    # =============================================================

    def test_retrieve_asset(self):
        asset = Asset.objects.create(
            name="Existing Laptop",
            asset_code="AST-003",
            category="IT Equipment",
            description="Existing asset",
            purchase_date="2026-01-15",
            purchase_cost="150000.00",
            status=Asset.Status.AVAILABLE,
            location=self.location,
            employee=None,
        )

        response = self.client.get(
            f"/api/v1/assets/{asset.id}/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["asset_code"],
            "AST-003",
        )

    # =============================================================
    # UPDATE
    # =============================================================

    def test_update_asset(self):
        asset = Asset.objects.create(
            name="Old Laptop",
            asset_code="AST-004",
            category="IT Equipment",
            description="Existing asset",
            purchase_date="2026-01-15",
            purchase_cost="150000.00",
            status=Asset.Status.AVAILABLE,
            location=self.location,
            employee=None,
        )

        response = self.client.patch(
            f"/api/v1/assets/{asset.id}/",
            {
                "name": "Updated Laptop",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        asset.refresh_from_db()

        self.assertEqual(
            asset.name,
            "Updated Laptop",
        )

    # =============================================================
    # DELETE
    # =============================================================

    def test_delete_asset(self):
        asset = Asset.objects.create(
            name="Delete Laptop",
            asset_code="AST-005",
            category="IT Equipment",
            description="Asset to delete",
            purchase_date="2026-01-15",
            purchase_cost="150000.00",
            status=Asset.Status.AVAILABLE,
            location=self.location,
            employee=None,
        )

        response = self.client.delete(
            f"/api/v1/assets/{asset.id}/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            Asset.objects.filter(id=asset.id).exists(),
        )

    # =============================================================
    # AUTHENTICATION
    # =============================================================

    def test_unauthenticated_user_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(
            "/api/v1/assets/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    # =============================================================
    # NEGATIVE PURCHASE COST
    # =============================================================

    def test_negative_purchase_cost_rejected(self):
        data = {
            **self.asset_data,
            "asset_code": "AST-006",
            "purchase_cost": "-100.00",
        }

        response = self.client.post(
            "/api/v1/assets/",
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    # =============================================================
    # ASSIGNED WITHOUT EMPLOYEE
    # =============================================================

    def test_assigned_asset_requires_employee(self):
        """Direct Asset registration cannot assign an employee."""
        data = {**self.asset_data, "asset_code": "AST-007",
                "status": Asset.Status.ASSIGNED, "employee": None}
        response = self.client.post("/api/v1/assets/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status", response.data)


    # =============================================================
    # ASSIGNED TO INACTIVE EMPLOYEE
    # =============================================================

    def test_assigned_asset_requires_active_employee(self):
        """The dedicated assignment workflow rejects inactive employees."""
        asset = Asset.objects.create(
            name="Inactive Assignment Laptop", asset_code="AST-008",
            category="IT Equipment", status=Asset.Status.AVAILABLE,
            location=self.location,
        )
        response = self.client.post(
            "/api/v1/assets/assignments/",
            {"asset": asset.id, "employee": self.inactive_employee.id,
             "assignment_date": "2026-09-18"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("employee", response.data)


    # =============================================================
    # VALID ASSIGNMENT
    # =============================================================

    def test_assigned_asset_to_active_employee(self):
        """Active assignment is created through AssetAssignment."""
        asset = Asset.objects.create(
            name="Assignment Laptop", asset_code="AST-009",
            category="IT Equipment", status=Asset.Status.AVAILABLE,
            location=self.location,
        )
        response = self.client.post(
            "/api/v1/assets/assignments/",
            {"asset": asset.id, "employee": self.employee.id,
             "assignment_date": "2026-09-18"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        assignment = AssetAssignment.objects.get(asset=asset)
        asset.refresh_from_db()
        self.assertEqual(assignment.employee_id, self.employee.id)
        self.assertEqual(assignment.status, AssetAssignment.Status.ACTIVE)
        self.assertEqual(asset.status, Asset.Status.ASSIGNED)
        self.assertEqual(asset.employee_id, self.employee.id)

    # =============================================================
    # ASSET HISTORY
    # =============================================================

    def test_asset_creation_creates_history_record(self):
        response = self.client.post(
            "/api/v1/assets/",
            self.asset_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        asset = Asset.objects.get(
            asset_code="AST-001",
        )

        history = AssetHistory.objects.filter(
            asset=asset,
            event_type=AssetHistory.EventType.CREATED,
        )

        self.assertEqual(history.count(), 1)

        record = history.first()

        self.assertEqual(
            record.performed_by,
            self.admin_user,
        )

        self.assertEqual(
            record.snapshot["asset_code"],
            "AST-001",
        )

        self.assertEqual(
            record.snapshot["name"],
            "Laptop",
        )


    def test_asset_assignment_creates_history_record(self):
        asset = Asset.objects.create(
            name="Assignment Laptop", asset_code="AST-HISTORY-001",
            category="IT Equipment", status=Asset.Status.AVAILABLE,
            location=self.location,
        )
        response = self.client.post(
            "/api/v1/assets/assignments/",
            {"asset": asset.id, "employee": self.employee.id,
             "assignment_date": "2026-09-18"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        record = AssetHistory.objects.get(
            asset=asset, event_type=AssetHistory.EventType.ASSIGNED
        )
        self.assertIsNone(record.previous_employee)
        self.assertEqual(record.new_employee, self.employee)
        self.assertEqual(record.performed_by, self.admin_user)



    def test_asset_unassignment_creates_history_record(self):
        asset = Asset.objects.create(
            name="Unassignment Laptop", asset_code="AST-HISTORY-002",
            category="IT Equipment", status=Asset.Status.AVAILABLE,
            location=self.location,
        )
        create_response = self.client.post(
            "/api/v1/assets/assignments/",
            {"asset": asset.id, "employee": self.employee.id,
             "assignment_date": "2026-09-18"},
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        assignment_id = create_response.data["id"]

        response = self.client.post(
            f"/api/v1/assets/assignments/{assignment_id}/return/",
            {"return_date": "2026-09-20"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        record = AssetHistory.objects.get(
            asset=asset, event_type=AssetHistory.EventType.UNASSIGNED
        )
        self.assertEqual(record.previous_employee, self.employee)
        self.assertIsNone(record.new_employee)

        asset.refresh_from_db()
        assignment = AssetAssignment.objects.get(pk=assignment_id)
        self.assertEqual(asset.status, Asset.Status.AVAILABLE)
        self.assertIsNone(asset.employee)
        self.assertEqual(assignment.status, AssetAssignment.Status.RETURNED)



    def test_asset_location_transfer_creates_history_record(self):
        new_location = Location.objects.create(
            location_code="LOC-TEST-002",
            name="Second Test Location",
        )

        asset = Asset.objects.create(
            name="Transfer Laptop",
            asset_code="AST-HISTORY-003",
            category="IT Equipment",
            description="Laptop for transfer test",
            purchase_date="2026-01-15",
            purchase_cost="150000.00",
            status=Asset.Status.AVAILABLE,
            location=self.location,
            employee=None,
        )

        response = self.client.patch(
            f"/api/v1/assets/{asset.id}/",
            {
                "location": new_location.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        history = AssetHistory.objects.filter(
            asset=asset,
            event_type=AssetHistory.EventType.TRANSFERRED,
        )

        self.assertEqual(history.count(), 1)

        record = history.first()

        self.assertEqual(
            record.previous_location,
            self.location,
        )

        self.assertEqual(
            record.new_location,
            new_location,
        )


    def test_asset_status_change_creates_history_record(self):
        asset = Asset.objects.create(
            name="Status Laptop",
            asset_code="AST-HISTORY-004",
            category="IT Equipment",
            description="Laptop for status test",
            status=Asset.Status.AVAILABLE,
            location=self.location,
            employee=None,
        )

        response = self.client.patch(
            f"/api/v1/assets/{asset.id}/",
            {
                "status": Asset.Status.RETIRED,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        history = AssetHistory.objects.filter(
            asset=asset,
            event_type=AssetHistory.EventType.RETIRED,
        )

        self.assertEqual(history.count(), 1)

        record = history.first()

        self.assertEqual(
            record.previous_status,
            Asset.Status.AVAILABLE,
        )

        self.assertEqual(
            record.new_status,
            Asset.Status.RETIRED,
        )


    def test_asset_condition_change_creates_history_record(self):
        asset = Asset.objects.create(
            name="Condition Laptop",
            asset_code="AST-HISTORY-005",
            category="IT Equipment",
            description="Laptop for condition test",
            status=Asset.Status.AVAILABLE,
            condition=Asset.Condition.GOOD,
            location=self.location,
            employee=None,
        )

        response = self.client.patch(
            f"/api/v1/assets/{asset.id}/",
            {
                "condition": Asset.Condition.FAIR,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        history = AssetHistory.objects.filter(
            asset=asset,
            event_type=AssetHistory.EventType.CONDITION_CHANGED,
        )

        self.assertEqual(history.count(), 1)

        record = history.first()

        self.assertIn(
            "Good",
            record.description,
        )

        self.assertIn(
            "Fair",
            record.description,
        )


    # =============================================================
    # ASSET DETAIL / HISTORY API
    # =============================================================

    def test_asset_detail_returns_history_and_maintenance(self):
        asset = Asset.objects.create(
            name="Detailed Laptop",
            asset_code="AST-DETAIL-001",
            category="IT Equipment",
            description="Detailed asset",
            purchase_date="2026-01-15",
            purchase_cost="150000.00",
            status=Asset.Status.AVAILABLE,
            location=self.location,
            employee=None,
        )

        AssetHistory.objects.create(
            asset=asset,
            event_type=AssetHistory.EventType.CREATED,
            performed_by=self.admin_user,
            description="Asset created.",
            snapshot={
                "asset_code": asset.asset_code,
                "name": asset.name,
            },
        )

        AssetMaintenance.objects.create(
            asset=asset,
            maintenance_date=date(2026, 3, 10),
            maintenance_type=AssetMaintenance.MaintenanceType.SERVICE,
            description="Routine service",
            service_provider="Test Service Provider",
            cost="25000.00",
            performed_by=self.admin_user,
        )

        response = self.client.get(
            f"/api/v1/assets/{asset.id}/detail/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIn(
            "asset",
            response.data,
        )

        self.assertIn(
            "history",
            response.data,
        )

        self.assertIn(
            "maintenance",
            response.data,
        )

        self.assertIn(
            "summary",
            response.data,
        )

        self.assertGreaterEqual(
            len(response.data["history"]),
            1,
        )

        self.assertEqual(
            len(response.data["maintenance"]),
            1,
        )

        self.assertEqual(
            response.data["summary"]["maintenance_count"],
            1,
        )


    def test_asset_history_endpoint_returns_history(self):
        asset = Asset.objects.create(
            name="History API Laptop",
            asset_code="AST-HISTORY-API-001",
            category="IT Equipment",
            status=Asset.Status.AVAILABLE,
            location=self.location,
        )

        AssetHistory.objects.create(
            asset=asset,
            event_type=AssetHistory.EventType.CREATED,
            performed_by=self.admin_user,
            description="Created.",
            snapshot={
                "asset_code": asset.asset_code,
            },
        )

        response = self.client.get(
            f"/api/v1/assets/{asset.id}/history/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

        self.assertEqual(
            response.data[0]["event_type"],
            AssetHistory.EventType.CREATED,
        )


    def test_asset_history_can_be_filtered_by_event_type(self):
        asset = Asset.objects.create(
            name="Filter Laptop",
            asset_code="AST-HISTORY-FILTER-001",
            category="IT Equipment",
            status=Asset.Status.AVAILABLE,
            location=self.location,
        )

        AssetHistory.objects.create(
            asset=asset,
            event_type=AssetHistory.EventType.CREATED,
            performed_by=self.admin_user,
            description="Created.",
        )

        AssetHistory.objects.create(
            asset=asset,
            event_type=AssetHistory.EventType.STATUS_CHANGED,
            performed_by=self.admin_user,
            previous_status=Asset.Status.AVAILABLE,
            new_status=Asset.Status.MAINTENANCE,
            description="Sent to maintenance.",
        )

        response = self.client.get(
            f"/api/v1/assets/{asset.id}/history/",
            {
                "event_type": AssetHistory.EventType.STATUS_CHANGED,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

        self.assertEqual(
            response.data[0]["event_type"],
            AssetHistory.EventType.STATUS_CHANGED,
        )


    # =============================================================
    # MAINTENANCE
    # =============================================================

    def test_create_maintenance_record(self):
        asset = Asset.objects.create(
            name="Maintenance Laptop",
            asset_code="AST-MAINT-001",
            category="IT Equipment",
            status=Asset.Status.MAINTENANCE,
            condition=Asset.Condition.FAIR,
            location=self.location,
        )

        data = {
            "asset": asset.id,
            "maintenance_date": "2026-04-10",
            "maintenance_type": AssetMaintenance.MaintenanceType.REPAIR,
            "description": "Screen replacement",
            "service_provider": "ABC Repairs",
            "cost": "75000.00",
            "condition_before": Asset.Condition.FAIR,
            "condition_after": Asset.Condition.GOOD,
            "next_maintenance_date": "2027-04-10",
            "reference": "REP-001",
            "notes": "Screen replaced successfully.",
        }

        response = self.client.post(
            "/api/v1/assets/maintenance/",
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        maintenance = AssetMaintenance.objects.get(
            asset=asset,
        )

        self.assertEqual(
            maintenance.cost,
            75000,
        )

        self.assertEqual(
            maintenance.performed_by,
            self.admin_user,
        )

        asset.refresh_from_db()

        self.assertEqual(
            asset.condition,
            Asset.Condition.GOOD,
        )

        self.assertEqual(
            asset.status,
            Asset.Status.AVAILABLE,
        )


    def test_negative_maintenance_cost_rejected(self):
        asset = Asset.objects.create(
            name="Maintenance Cost Test",
            asset_code="AST-MAINT-002",
            category="IT Equipment",
            status=Asset.Status.MAINTENANCE,
            location=self.location,
        )

        data = {
            "asset": asset.id,
            "maintenance_date": "2026-04-10",
            "maintenance_type": AssetMaintenance.MaintenanceType.REPAIR,
            "description": "Invalid maintenance",
            "cost": "-100.00",
        }

        response = self.client.post(
            "/api/v1/assets/maintenance/",
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


    def test_invalid_next_maintenance_date_rejected(self):
        asset = Asset.objects.create(
            name="Maintenance Date Test",
            asset_code="AST-MAINT-003",
            category="IT Equipment",
            status=Asset.Status.MAINTENANCE,
            location=self.location,
        )

        data = {
            "asset": asset.id,
            "maintenance_date": "2026-04-10",
            "maintenance_type": AssetMaintenance.MaintenanceType.SERVICE,
            "description": "Invalid service schedule",
            "cost": "10000.00",
            "next_maintenance_date": "2026-03-01",
        }

        response = self.client.post(
            "/api/v1/assets/maintenance/",
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


    def test_maintenance_creates_asset_history(self):
        asset = Asset.objects.create(
            name="Maintenance History Test",
            asset_code="AST-MAINT-004",
            category="IT Equipment",
            status=Asset.Status.MAINTENANCE,
            location=self.location,
        )

        data = {
            "asset": asset.id,
            "maintenance_date": "2026-05-10",
            "maintenance_type": AssetMaintenance.MaintenanceType.SERVICE,
            "description": "Routine maintenance",
            "cost": "15000.00",
        }

        response = self.client.post(
            "/api/v1/assets/maintenance/",
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        history = AssetHistory.objects.filter(
            asset=asset,
            event_type=AssetHistory.EventType.MAINTENANCE,
        )

        self.assertEqual(
            history.count(),
            1,
        )

        record = history.first()

        self.assertEqual(
            record.performed_by,
            self.admin_user,
        )

        self.assertIn(
            "Routine maintenance",
            record.description,
        )


    def test_maintenance_history_endpoint_returns_records(self):
        asset = Asset.objects.create(
            name="Maintenance API Test",
            asset_code="AST-MAINT-005",
            category="IT Equipment",
            location=self.location,
        )

        AssetMaintenance.objects.create(
            asset=asset,
            maintenance_date=date(2026, 2, 10),
            maintenance_type=AssetMaintenance.MaintenanceType.SERVICE,
            description="February service",
            cost="10000.00",
            performed_by=self.admin_user,
        )

        AssetMaintenance.objects.create(
            asset=asset,
            maintenance_date=date(2026, 6, 10),
            maintenance_type=AssetMaintenance.MaintenanceType.REPAIR,
            description="June repair",
            cost="30000.00",
            performed_by=self.admin_user,
        )

        response = self.client.get(
            f"/api/v1/assets/{asset.id}/maintenance-history/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            2,
        )

        self.assertEqual(
            response.data[0]["maintenance_type"],
            AssetMaintenance.MaintenanceType.REPAIR,
        )


    def test_maintenance_history_can_be_date_filtered(self):
        asset = Asset.objects.create(
            name="Maintenance Filter Test",
            asset_code="AST-MAINT-006",
            category="IT Equipment",
            location=self.location,
        )

        AssetMaintenance.objects.create(
            asset=asset,
            maintenance_date=date(2026, 2, 10),
            maintenance_type=AssetMaintenance.MaintenanceType.SERVICE,
            description="February service",
            cost="10000.00",
            performed_by=self.admin_user,
        )

        AssetMaintenance.objects.create(
            asset=asset,
            maintenance_date=date(2026, 8, 10),
            maintenance_type=AssetMaintenance.MaintenanceType.REPAIR,
            description="August repair",
            cost="30000.00",
            performed_by=self.admin_user,
        )

        response = self.client.get(
            f"/api/v1/assets/{asset.id}/maintenance-history/",
            {
                "date_from": "2026-07-01",
                "date_to": "2026-08-31",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

        self.assertEqual(
            response.data[0]["maintenance_type"],
            AssetMaintenance.MaintenanceType.REPAIR,
        )

# =============================================================
# DEDICATED ASSET ASSIGNMENT WORKFLOW
# =============================================================

def test_asset_registration_ignores_employee_field(self):
    response = self.client.post(
        "/api/v1/assets/",
        {**self.asset_data, "employee": self.employee.id},
        format="json",
    )
    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    asset = Asset.objects.get(asset_code="AST-001")
    self.assertIsNone(asset.employee)
    self.assertFalse(AssetAssignment.objects.filter(
        asset=asset, status=AssetAssignment.Status.ACTIVE
    ).exists())

def test_asset_update_rejects_manual_assigned_status(self):
    asset = Asset.objects.create(
        name="Manual Assignment Test", asset_code="AST-ASG-010",
        category="IT Equipment", status=Asset.Status.AVAILABLE,
        location=self.location,
    )
    response = self.client.patch(
        f"/api/v1/assets/{asset.id}/",
        {"status": Asset.Status.ASSIGNED},
        format="json",
    )
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    asset.refresh_from_db()
    self.assertEqual(asset.status, Asset.Status.AVAILABLE)

def test_asset_cannot_have_two_active_assignments(self):
    asset = Asset.objects.create(
        name="Duplicate Assignment Laptop", asset_code="AST-ASG-011",
        category="IT Equipment", status=Asset.Status.AVAILABLE,
        location=self.location,
    )
    first = self.client.post(
        "/api/v1/assets/assignments/",
        {"asset": asset.id, "employee": self.employee.id,
         "assignment_date": "2026-09-18"},
        format="json",
    )
    self.assertEqual(first.status_code, status.HTTP_201_CREATED)
    second = self.client.post(
        "/api/v1/assets/assignments/",
        {"asset": asset.id, "employee": self.inactive_employee.id,
         "assignment_date": "2026-09-19"},
        format="json",
    )
    self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
    self.assertEqual(
        AssetAssignment.objects.filter(
            asset=asset, status=AssetAssignment.Status.ACTIVE
        ).count(),
        1,
    )

def test_assignment_expected_return_date_cannot_precede_assignment_date(self):
    asset = Asset.objects.create(
        name="Return Date Laptop", asset_code="AST-ASG-012",
        category="IT Equipment", status=Asset.Status.AVAILABLE,
        location=self.location,
    )
    response = self.client.post(
        "/api/v1/assets/assignments/",
        {"asset": asset.id, "employee": self.employee.id,
         "assignment_date": "2026-09-20",
         "expected_return_date": "2026-09-19"},
        format="json",
    )
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    self.assertIn("expected_return_date", response.data)

def test_return_date_cannot_precede_assignment_date(self):
    asset = Asset.objects.create(
        name="Invalid Return Laptop", asset_code="AST-ASG-013",
        category="IT Equipment", status=Asset.Status.AVAILABLE,
        location=self.location,
    )
    create_response = self.client.post(
        "/api/v1/assets/assignments/",
        {"asset": asset.id, "employee": self.employee.id,
         "assignment_date": "2026-09-20"},
        format="json",
    )
    self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
    assignment_id = create_response.data["id"]
    response = self.client.post(
        f"/api/v1/assets/assignments/{assignment_id}/return/",
        {"return_date": "2026-09-19"},
        format="json",
    )
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

def test_returned_assignment_cannot_be_returned_again(self):
    asset = Asset.objects.create(
        name="Double Return Laptop", asset_code="AST-ASG-014",
        category="IT Equipment", status=Asset.Status.AVAILABLE,
        location=self.location,
    )
    create_response = self.client.post(
        "/api/v1/assets/assignments/",
        {"asset": asset.id, "employee": self.employee.id,
         "assignment_date": "2026-09-18"},
        format="json",
    )
    self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
    assignment_id = create_response.data["id"]
    first_return = self.client.post(
        f"/api/v1/assets/assignments/{assignment_id}/return/",
        {"return_date": "2026-09-20"},
        format="json",
    )
    self.assertEqual(first_return.status_code, status.HTTP_200_OK)
    second_return = self.client.post(
        f"/api/v1/assets/assignments/{assignment_id}/return/",
        {"return_date": "2026-09-21"},
        format="json",
    )
    self.assertEqual(second_return.status_code, status.HTTP_400_BAD_REQUEST)

def test_asset_detail_includes_assignment_history(self):
    asset = Asset.objects.create(
        name="Assignment Detail Laptop", asset_code="AST-ASG-015",
        category="IT Equipment", status=Asset.Status.AVAILABLE,
        location=self.location,
    )
    response = self.client.post(
        "/api/v1/assets/assignments/",
        {"asset": asset.id, "employee": self.employee.id,
         "assignment_date": "2026-09-18"},
        format="json",
    )
    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    detail = self.client.get(f"/api/v1/assets/{asset.id}/detail/")
    self.assertEqual(detail.status_code, status.HTTP_200_OK)
    self.assertIn("assignments", detail.data)
    self.assertEqual(len(detail.data["assignments"]), 1)
    self.assertEqual(
        detail.data["assignments"][0]["status"],
        AssetAssignment.Status.ACTIVE,
    )

def test_current_assignments_endpoint_returns_active_assignments(self):
    asset = Asset.objects.create(
        name="Current Assignment Laptop", asset_code="AST-ASG-016",
        category="IT Equipment", status=Asset.Status.AVAILABLE,
        location=self.location,
    )
    response = self.client.post(
        "/api/v1/assets/assignments/",
        {"asset": asset.id, "employee": self.employee.id,
         "assignment_date": "2026-09-18"},
        format="json",
    )
    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    current = self.client.get("/api/v1/assets/assignments/current/")
    self.assertEqual(current.status_code, status.HTTP_200_OK)
    self.assertEqual(len(current.data), 1)
    self.assertEqual(current.data[0]["asset"], asset.id)
