from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from authentication.models import Permission, Role, RolePermission, User, UserRole
from company.models import Supplier
from finance.models import Expense, ExpenseCategory


class ReportSecurityTests(TestCase):
    """Regression tests for role-filtered dashboard/search/notification data."""

    def setUp(self):
        self.client = APIClient()

        self.admin = self.make_user(
            "admin",
            "Admin",
            [
                "REPORTS_READ",
                "FINANCE_READ",
                "INVENTORY_READ",
                "FLEET_READ",
                "ASSET_READ",
                "PROCUREMENT_READ",
            ],
        )
        self.finance = self.make_user(
            "finance",
            "Finance Staff",
            ["REPORTS_READ", "FINANCE_READ"],
        )
        self.inventory = self.make_user(
            "inventory",
            "Inventory Staff",
            ["REPORTS_READ", "INVENTORY_READ"],
        )
        self.manager = self.make_user(
            "manager",
            "Manager",
            [
                "REPORTS_READ",
                "FINANCE_READ",
                "INVENTORY_READ",
                "FLEET_READ",
                "ASSET_READ",
                "PROCUREMENT_READ",
            ],
        )

        category = ExpenseCategory.objects.create(name="Testing")
        self.expense = Expense.objects.create(
            category=category,
            expense_number="EXP-TEST-001",
            expense_date=date(2026, 1, 15),
            description="Restricted finance test expense",
            amount="125000.00",
            status=Expense.Status.PENDING,
        )

    def make_user(self, username, role_name, permission_codes):
        user = User.objects.create_user(
            username=f"{username}@test",
            password="test-password",
            status=User.Status.ACTIVE,
        )
        role, _ = Role.objects.get_or_create(name=role_name)

        for code in permission_codes:
            permission, _ = Permission.objects.get_or_create(
                permission_code=code
            )
            RolePermission.objects.get_or_create(
                role=role,
                permission=permission,
            )

        UserRole.objects.create(user=user, role=role)
        return user

    def test_finance_staff_can_see_financial_dashboard_amounts(self):
        self.client.force_authenticate(self.finance)

        response = self.client.get("/api/v1/reports/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("finance", response.data)
        self.assertEqual(
            str(response.data["finance"]["total_expenses"]),
            "125000.00",
        )

    def test_admin_can_see_financial_dashboard_amounts(self):
        self.client.force_authenticate(self.admin)

        response = self.client.get("/api/v1/reports/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("finance", response.data)

    def test_manager_does_not_see_shared_financial_amounts(self):
        self.client.force_authenticate(self.manager)

        response = self.client.get("/api/v1/reports/dashboard/")

        self.assertEqual(response.status_code, 200)
        finance = response.data.get("finance")
        self.assertTrue(
            finance is None or finance == {},
            "Manager must not receive shared dashboard financial amounts.",
        )

    def test_inventory_staff_does_not_see_financial_dashboard_amounts(self):
        self.client.force_authenticate(self.inventory)

        response = self.client.get("/api/v1/reports/dashboard/")

        self.assertEqual(response.status_code, 200)
        finance = response.data.get("finance")
        self.assertTrue(
            finance is None or finance == {},
            "Inventory Staff must not receive shared dashboard financial amounts.",
        )

    def test_inventory_staff_cannot_find_finance_records(self):
        self.client.force_authenticate(self.inventory)

        response = self.client.get(
            "/api/v1/reports/search/",
            {"q": self.expense.expense_number},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            any(
                result.get("type") == "finance"
                for result in response.data.get("results", [])
            )
        )

    def test_inventory_staff_does_not_receive_finance_notifications(self):
        self.client.force_authenticate(self.inventory)

        response = self.client.get("/api/v1/reports/notifications/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            any(
                notification.get("type") == "finance"
                for notification in response.data.get("notifications", [])
            )
        )
