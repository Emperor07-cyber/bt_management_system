from django.test import TestCase
from rest_framework.test import APITestCase

from authentication.models import Permission, Role, RolePermission, User, UserRole

from .models import (
    CompanySetting,
    Department,
    Employee,
    EmployeeModuleAffiliation,
    Location,
    Supplier,
)
from .serializers import (
    CompanySettingSerializer,
    DepartmentSerializer,
    EmployeeModuleAffiliationSerializer,
    EmployeeSerializer,
    LocationSerializer,
    SupplierSerializer,
)


class CompanyAPITests(APITestCase):
    def setUp(self):
        self.procurement_user = User.objects.create_user(
            "company_procurement_test",
            password="pass1234",
        )

        role = Role.objects.create(name="Company Procurement Test Role")

        for action in ("READ", "CREATE", "UPDATE", "DELETE"):
            permission = Permission.objects.create(
                permission_code=f"PROCUREMENT_{action}",
            )
            RolePermission.objects.create(role=role, permission=permission)

        UserRole.objects.create(user=self.procurement_user, role=role)
        self.client.force_authenticate(self.procurement_user)

    def test_supplier_is_available_to_procurement_roles(self):
        response = self.client.post(
            "/api/v1/company/suppliers/",
            {"supplier_code": "SUP-001", "name": "ABC Supplies"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

        supplier_id = response.data["id"]

        response = self.client.patch(
            f"/api/v1/company/suppliers/{supplier_id}/",
            {"phone": "08000000000"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.delete(
            f"/api/v1/company/suppliers/{supplier_id}/",
        )
        self.assertEqual(response.status_code, 204)

    def test_duplicate_supplier_code_is_rejected(self):
        Supplier.objects.create(
            supplier_code="SUP-002",
            name="Existing",
        )

        response = self.client.post(
            "/api/v1/company/suppliers/",
            {"supplier_code": "SUP-002", "name": "Duplicate"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_company_general_endpoints_do_not_bypass_company_permission(self):
        for endpoint in ("departments", "locations", "employees", "settings"):
            response = self.client.get(f"/api/v1/company/{endpoint}/")
            self.assertEqual(response.status_code, 403, endpoint)

    def test_inventory_role_cannot_access_suppliers(self):
        role = Role.objects.create(name="Inventory Only Company Test")
        permission = Permission.objects.create(permission_code="INVENTORY_READ")
        RolePermission.objects.create(role=role, permission=permission)

        user = User.objects.create_user(
            "company_inventory_test",
            password="pass1234",
        )
        UserRole.objects.create(user=user, role=role)
        self.client.force_authenticate(user)

        response = self.client.get("/api/v1/company/suppliers/")
        self.assertEqual(response.status_code, 403)

    def test_supplier_list_is_readable_by_procurement_role(self):
        Supplier.objects.create(
            supplier_code="SUP-003",
            name="Readable Supplier",
        )
        response = self.client.get("/api/v1/company/suppliers/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)


class CompanySerializerTests(TestCase):
    def setUp(self):
        self.location = Location.objects.create(
            location_code="HQ",
            name="Head Office",
        )
        self.department = Department.objects.create(
            department_code="IT",
            name="Information Technology",
        )
        self.employee = Employee.objects.create(
            employee_number="EMP-001",
            first_name="John",
            last_name="Doe",
            department=self.department,
            location=self.location,
            status=Employee.Status.ACTIVE,
        )

    def test_employee_can_have_fleet_affiliation(self):
        affiliation = EmployeeModuleAffiliationSerializer(
            data={
                "employee": self.employee.id,
                "module": "FLEET",
                "function": "Driver",
                "is_active": True,
            }
        )
        self.assertTrue(affiliation.is_valid(), affiliation.errors)
        obj = affiliation.save()
        self.assertEqual(obj.module, "FLEET")
        self.assertEqual(obj.function, "Driver")

    def test_employee_can_belong_to_multiple_modules(self):
        EmployeeModuleAffiliation.objects.create(
            employee=self.employee,
            module="FLEET",
            function="Driver",
        )
        EmployeeModuleAffiliation.objects.create(
            employee=self.employee,
            module="ASSETS",
            function="Asset Custodian",
        )
        self.assertEqual(self.employee.module_affiliations.count(), 2)

    def test_inactive_employee_cannot_have_active_affiliation(self):
        self.employee.status = Employee.Status.INACTIVE
        self.employee.save()

        serializer = EmployeeModuleAffiliationSerializer(
            data={
                "employee": self.employee.id,
                "module": "FLEET",
                "function": "Driver",
                "is_active": True,
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("employee", serializer.errors)

    def test_employee_cannot_use_inactive_department(self):
        self.department.is_active = False
        self.department.save()

        serializer = EmployeeSerializer(
            data={
                "employee_number": "EMP-002",
                "first_name": "Jane",
                "last_name": "Doe",
                "department": self.department.id,
                "status": "ACTIVE",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("department", serializer.errors)

    def test_employee_cannot_use_inactive_location(self):
        self.location.is_active = False
        self.location.save()

        serializer = EmployeeSerializer(
            data={
                "employee_number": "EMP-002",
                "first_name": "Jane",
                "last_name": "Doe",
                "location": self.location.id,
                "status": "ACTIVE",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("location", serializer.errors)

    def test_location_cannot_be_its_own_parent(self):
        location = Location.objects.create(
            location_code="BRANCH",
            name="Branch",
        )
        serializer = LocationSerializer(
            location,
            data={
                "location_code": "BRANCH",
                "name": "Branch",
                "parent": location.id,
                "is_active": True,
            },
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("parent", serializer.errors)

    def test_location_cannot_have_inactive_parent(self):
        parent = Location.objects.create(
            location_code="PARENT",
            name="Parent Location",
            is_active=False,
        )
        serializer = LocationSerializer(
            data={
                "location_code": "CHILD",
                "name": "Child Location",
                "parent": parent.id,
                "is_active": True,
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("parent", serializer.errors)

    def test_department_manager_must_be_active(self):
        self.employee.status = Employee.Status.INACTIVE
        self.employee.save()

        serializer = DepartmentSerializer(
            self.department,
            data={
                "department_code": "IT",
                "name": "Information Technology",
                "manager": self.employee.id,
                "is_active": True,
            },
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("manager", serializer.errors)

    def test_department_manager_must_belong_to_department(self):
        other_department = Department.objects.create(
            department_code="FIN",
            name="Finance",
        )
        self.employee.department = other_department
        self.employee.save()

        serializer = DepartmentSerializer(
            self.department,
            data={
                "department_code": "IT",
                "name": "Information Technology",
                "manager": self.employee.id,
                "is_active": True,
            },
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("manager", serializer.errors)

    def test_supplier_name_cannot_be_blank(self):
        serializer = SupplierSerializer(
            data={
                "supplier_code": "SUP-001",
                "name": "   ",
                "is_active": True,
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)

    def test_valid_supplier(self):
        serializer = SupplierSerializer(
            data={
                "supplier_code": "SUP-001",
                "name": "ABC Supplies Ltd",
                "is_active": True,
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_first_company_setting_is_valid(self):
        serializer = CompanySettingSerializer(
            data={
                "company_name": "BT Management",
                "company_code": "BT",
                "currency_code": "NGN",
                "timezone": "Africa/Lagos",
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_second_company_setting_is_rejected(self):
        CompanySetting.objects.create(
            company_name="BT Management",
            company_code="BT",
            currency_code="NGN",
            timezone="Africa/Lagos",
        )
        serializer = CompanySettingSerializer(
            data={
                "company_name": "Another Company",
                "company_code": "OTHER",
                "currency_code": "NGN",
                "timezone": "Africa/Lagos",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)

    def test_currency_code_is_normalized(self):
        serializer = CompanySettingSerializer(
            data={
                "company_name": "BT Management",
                "company_code": "BT",
                "currency_code": "ngn",
                "timezone": "Africa/Lagos",
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["currency_code"], "NGN")
