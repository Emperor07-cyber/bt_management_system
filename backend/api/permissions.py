from rest_framework.permissions import BasePermission


class HasPermissionCode(BasePermission):
    """
    Checks whether the authenticated user has
    a specific application permission.
    """

    required_permission = None

    def has_permission(
        self,
        request,
        view,
    ):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        permission_code = getattr(
            view,
            "required_permission",
            None,
        )

        if not permission_code:
            return True

        return user.user_roles.filter(
            role__role_permissions__permission__permission_code=permission_code
        ).exists()