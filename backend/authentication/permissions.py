from rest_framework.permissions import BasePermission

from .models import RolePermission


class RoleBasedPermission(BasePermission):
    """
    Application-level permission system.

    User
        ↓
    UserRole
        ↓
    Role
        ↓
    RolePermission
        ↓
    Permission
    """

    MODULE_MAP = {
        "inventory": "INVENTORY",
        "fleet": "FLEET",
        "assets": "ASSET",
        "finance": "FINANCE",
        "procurement": "PROCUREMENT",
        "reports": "REPORTS",
        "company": "COMPANY",
    }

    ACTION_MAP = {
        "GET": "READ",
        "HEAD": "READ",
        "OPTIONS": "READ",
        "POST": "CREATE",
        "PUT": "UPDATE",
        "PATCH": "UPDATE",
        "DELETE": "DELETE",
    }

    @classmethod
    def user_has_permission(cls, user, permission_code):
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "status", None) != "ACTIVE":
            return False
        return RolePermission.objects.filter(
            role__user_roles__user=user,
            permission__permission_code=permission_code,
        ).exists()

    @classmethod
    def user_has_module_permission(cls, user, module, action="READ"):
        return cls.user_has_permission(user, f"{module}_{action}")

    @classmethod
    def is_financial_data_role(cls, user):
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "is_superuser", False):
            return True
        if getattr(user, "status", None) != "ACTIVE":
            return False
        return RolePermission.objects.filter(
            role__user_roles__user=user,
            role__name__in=["Admin", "Finance Staff"],
        ).exists()

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if getattr(user, "status", None) != "ACTIVE":
            return False

        module = self.get_module(request)

        if not module:
            return False

        action = self.ACTION_MAP.get(request.method)

        if not action:
            return False

        return self.user_has_module_permission(user, module, action)

    def get_module(self, request):
        path = request.path.lower()

        # Fleet needs read-only access to employees and locations
        # because these are used when creating vehicle assignments.
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            if "/company/employees/" in path:
                return "FLEET"

            if "/company/locations/" in path:
                return "FLEET"

        # Suppliers are shared by Company and Procurement.
        if "/company/suppliers/" in path:
            return "PROCUREMENT"

        for url_module, permission_module in self.MODULE_MAP.items():
            if f"/{url_module}/" in path:
                return permission_module

        return None
