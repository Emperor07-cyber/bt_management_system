from rest_framework.test import APITestCase

from authentication.models import Permission, Role, RolePermission, User, UserRole
from company.models import Employee, Location, Supplier
from .models import ExpenseCategory, Expense, ExpensePayment


class FinanceAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("finance_test", password="pass1234")
        role = Role.objects.create(name="Finance Test Role")
        for action in ("READ", "CREATE", "UPDATE", "DELETE"):
            permission = Permission.objects.create(permission_code=f"FINANCE_{action}")
            RolePermission.objects.create(role=role, permission=permission)
        UserRole.objects.create(user=self.user, role=role)
        self.client.force_authenticate(self.user)
        self.category = ExpenseCategory.objects.create(name="Utilities")
        self.supplier = Supplier.objects.create(supplier_code="SUP-FIN", name="Finance Supplier")
        self.employee = Employee.objects.create(employee_number="EMP-FIN", first_name="Finance", last_name="User")
        self.location = Location.objects.create(location_code="LOC-FIN", name="Finance Office")
        self.expense = Expense.objects.create(
            category=self.category, supplier=self.supplier, employee=self.employee,
            location=self.location, expense_number="EXP-001", expense_date="2026-09-10",
            description="Electricity", amount="100000.00",
        )

    def test_expense_category_crud(self):
        response = self.client.post("/api/v1/finance/expense-categories/", {"name": "Travel"}, format="json")
        self.assertEqual(response.status_code, 201)
        category_id = response.data["id"]
        response = self.client.patch(f"/api/v1/finance/expense-categories/{category_id}/", {"description": "Updated"}, format="json")
        self.assertEqual(response.status_code, 200)
        response = self.client.delete(f"/api/v1/finance/expense-categories/{category_id}/")
        self.assertEqual(response.status_code, 204)

    def test_expense_crud_and_duplicate_number(self):
        payload = {
            "category": self.category.id, "expense_number": "EXP-002",
            "expense_date": "2026-09-10", "description": "Fuel", "amount": "25000.00",
        }
        response = self.client.post("/api/v1/finance/expenses/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        duplicate = self.client.post("/api/v1/finance/expenses/", payload, format="json")
        self.assertEqual(duplicate.status_code, 400)

    def test_expense_payment_marks_expense_paid(self):
        response = self.client.post("/api/v1/finance/expense-payments/", {
            "expense": self.expense.id, "payment_date": "2026-09-10",
            "amount": "100000.00", "payment_method": "BANK_TRANSFER",
        }, format="json")
        self.assertEqual(response.status_code, 201)
        self.expense.refresh_from_db()
        self.assertEqual(self.expense.status, Expense.Status.PAID)

    def test_partial_expense_payment_sets_approved(self):
        response = self.client.post("/api/v1/finance/expense-payments/", {
            "expense": self.expense.id, "payment_date": "2026-09-10",
            "amount": "25000.00", "payment_method": "CASH",
        }, format="json")
        self.assertEqual(response.status_code, 201)
        self.expense.refresh_from_db()
        self.assertEqual(self.expense.status, Expense.Status.APPROVED)

    def test_finance_amount_is_decimal(self):
        response = self.client.get(f"/api/v1/finance/expenses/{self.expense.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.data["amount"]), "100000.00")

    def test_unauthenticated_finance_request_is_denied(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/v1/finance/expenses/")
        self.assertIn(response.status_code, (401, 403))
