from django.test import TestCase
from rest_framework.test import APIRequestFactory

from .models import Permission, Role, RolePermission, User, UserRole
from .permissions import RoleBasedPermission


class RoleBasedPermissionTests(TestCase):
    """Regression tests for the application RBAC matrix."""

    ROLE_PERMISSIONS = {
        "Admin": ["INVENTORY", "FLEET", "ASSET", "FINANCE", "PROCUREMENT"],
        "Manager": ["INVENTORY", "FLEET", "ASSET", "FINANCE", "PROCUREMENT"],
        "Inventory Staff": ["INVENTORY"],
        "Fleet Staff": ["FLEET"],
        "Asset Staff": ["ASSET"],
        "Procurement Staff": ["PROCUREMENT"],
        "Finance Staff": ["FINANCE"],
        "Read Only": ["INVENTORY", "FLEET", "ASSET", "FINANCE", "PROCUREMENT"],
    }

    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = RoleBasedPermission()

        for role_name, modules in self.ROLE_PERMISSIONS.items():
            role = Role.objects.create(name=role_name)
            actions = ["READ", "CREATE", "UPDATE", "DELETE"]
            if role_name == "Manager":
                actions = ["READ", "CREATE", "UPDATE"]
            if role_name == "Read Only":
                actions = ["READ"]

            for module in modules:
                for action in actions:
                    permission, _ = Permission.objects.get_or_create(
                        permission_code=f"{module}_{action}"
                    )
                    RolePermission.objects.create(
                        role=role,
                        permission=permission,
                    )

            if role_name != "Read Only":
                reports, _ = Permission.objects.get_or_create(
                    permission_code="REPORTS_READ"
                )
                RolePermission.objects.create(
                    role=role,
                    permission=reports,
                )
            else:
                reports, _ = Permission.objects.get_or_create(
                    permission_code="REPORTS_READ"
                )
                RolePermission.objects.create(
                    role=role,
                    permission=reports,
                )

    def user_for_role(self, role_name, status=User.Status.ACTIVE):
        user = User.objects.create_user(
            username=f"{role_name.lower().replace(' ', '_')}@test",
            password="test-password",
            status=status,
        )
        role = Role.objects.get(name=role_name)
        UserRole.objects.create(user=user, role=role)
        return user

    def allowed(self, user, method, path):
        request = getattr(self.factory, method.lower())(path)
        request.user = user
        return self.permission.has_permission(request, None)

    def test_admin_has_full_crud_access(self):
        user = self.user_for_role("Admin")

        for method in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            self.assertTrue(
                self.allowed(user, method, "/api/v1/inventory/items/")
            )

    def test_manager_can_create_and_update_but_not_delete(self):
        user = self.user_for_role("Manager")

        self.assertTrue(self.allowed(user, "GET", "/api/v1/inventory/items/"))
        self.assertTrue(self.allowed(user, "POST", "/api/v1/inventory/items/"))
        self.assertTrue(self.allowed(user, "PATCH", "/api/v1/inventory/items/"))
        self.assertFalse(self.allowed(user, "DELETE", "/api/v1/inventory/items/"))

    def test_module_staff_can_only_access_their_module(self):
        cases = {
            "Inventory Staff": ("inventory", "fleet"),
            "Fleet Staff": ("fleet", "inventory"),
            "Asset Staff": ("assets", "inventory"),
            "Procurement Staff": ("procurement", "inventory"),
            "Finance Staff": ("finance", "inventory"),
        }

        for role_name, (allowed_module, denied_module) in cases.items():
            with self.subTest(role=role_name):
                user = self.user_for_role(role_name)
                self.assertTrue(
                    self.allowed(
                        user,
                        "GET",
                        f"/api/v1/{allowed_module}/items/",
                    )
                )
                self.assertFalse(
                    self.allowed(
                        user,
                        "GET",
                        f"/api/v1/{denied_module}/items/",
                    )
                )

    def test_read_only_cannot_create_update_or_delete(self):
        user = self.user_for_role("Read Only")

        self.assertTrue(self.allowed(user, "GET", "/api/v1/inventory/items/"))
        self.assertFalse(self.allowed(user, "POST", "/api/v1/inventory/items/"))
        self.assertFalse(self.allowed(user, "PATCH", "/api/v1/inventory/items/"))
        self.assertFalse(self.allowed(user, "DELETE", "/api/v1/inventory/items/"))

    def test_inactive_user_is_denied_even_with_a_role(self):
        user = self.user_for_role("Admin", status=User.Status.INACTIVE)

        self.assertFalse(self.allowed(user, "GET", "/api/v1/inventory/items/"))

    def test_supplier_endpoint_uses_procurement_permissions(self):
        procurement_user = self.user_for_role("Procurement Staff")
        inventory_user = self.user_for_role("Inventory Staff")

        path = "/api/v1/company/suppliers/"

        self.assertTrue(self.allowed(procurement_user, "GET", path))
        self.assertFalse(self.allowed(inventory_user, "GET", path))
