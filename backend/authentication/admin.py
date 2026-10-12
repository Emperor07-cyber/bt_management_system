from django.contrib import admin

from .models import (
    Role,
    Permission,
    UserRole,
    RolePermission,
)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "description",
        "created_at",
    )
    search_fields = (
        "name",
        "description",
    )


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "permission_code",
        "description",
    )
    search_fields = (
        "permission_code",
        "description",
    )


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "role",
    )
    search_fields = (
        "user__username",
        "role__name",
    )


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "role",
        "permission",
    )
    search_fields = (
        "role__name",
        "permission__permission_code",
    )