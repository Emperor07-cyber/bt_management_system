
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):

    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError("Username is required")

        user = self.model(
            username=username,
            **extra_fields,
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(
            username,
            password,
            **extra_fields,
        )


class Role(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
    )

    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "roles"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Permission(models.Model):
    permission_code = models.CharField(
        max_length=100,
        unique=True,
    )

    description = models.TextField(blank=True)

    class Meta:
        db_table = "permissions"
        ordering = ["permission_code"]

    def __str__(self):
        return self.permission_code


class User(AbstractBaseUser, PermissionsMixin):

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"
        LOCKED = "LOCKED", "Locked"

    employee = models.OneToOneField(
    "company.Employee",
    on_delete=models.CASCADE,
    related_name="user_account",
    null=True,
    blank=True,
)

    username = models.CharField(
        max_length=100,
        unique=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    # class Role(models.TextChoices):
    #     ADMIN = "ADMIN", "Admin"
    #     MANAGER = "MANAGER", "Manager"
    #     STAFF = "STAFF", "Staff"
    #     READ_ONLY = "READ_ONLY", "Read Only"

    # role = models.CharField(
    #     max_length=20,
    #     choices=Role.choices,
    #     default=Role.STAFF,
    # )

    is_staff = models.BooleanField(default=False)

    last_login_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "username"

    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.username


class UserRole(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="user_roles",
    )

    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="user_roles",
    )

    class Meta:
        db_table = "user_roles"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "role"],
                name="unique_user_role",
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.role.name}"


class RolePermission(models.Model):
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="role_permissions",
    )

    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name="role_permissions",
    )

    class Meta:
        db_table = "role_permissions"
        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission"],
                name="unique_role_permission",
            )
        ]

    def __str__(self):
        return f"{self.role.name} - {self.permission.permission_code}"
