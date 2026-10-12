from django.core.management.base import BaseCommand
from authentication.models import Role, Permission, RolePermission


class Command(BaseCommand):
    help = "Create Company permissions and safely assign them to the existing Admin role."

    COMPANY_PERMISSIONS = [
        (
            "COMPANY_CREATE",
            "Create company records such as employees, departments, locations, suppliers, and settings.",
        ),
        (
            "COMPANY_READ",
            "View company records such as employees, departments, locations, suppliers, and settings.",
        ),
        (
            "COMPANY_UPDATE",
            "Update company records such as employees, departments, locations, suppliers, and settings.",
        ),
        (
            "COMPANY_DELETE",
            "Delete company records such as employees, departments, locations, suppliers, and settings.",
        ),
    ]

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.NOTICE(
                "Setting up Company permissions..."
            )
        )

        # ---------------------------------------------------------
        # 1. Find the existing Admin role.
        # ---------------------------------------------------------
        try:
            admin_role = Role.objects.get(name="Admin")
        except Role.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    "Admin role does not exist. "
                    "No permissions were created or assigned."
                )
            )
            return

        self.stdout.write(
            f"Using existing role: {admin_role.name}"
        )

        created_permissions = 0
        existing_permissions = 0
        assigned_permissions = 0
        existing_assignments = 0

        # ---------------------------------------------------------
        # 2. Create each Company permission if it does not exist.
        # ---------------------------------------------------------
        for permission_code, description in self.COMPANY_PERMISSIONS:

            permission, created = Permission.objects.get_or_create(
                permission_code=permission_code,
                defaults={
                    "description": description,
                },
            )

            if created:
                created_permissions += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created permission: {permission_code}"
                    )
                )
            else:
                existing_permissions += 1

                self.stdout.write(
                    f"Permission already exists: {permission_code}"
                )

            # -----------------------------------------------------
            # 3. Safely assign the permission to Admin.
            #
            # get_or_create prevents duplicate assignments.
            # Existing users, roles and permissions are untouched.
            # -----------------------------------------------------
            role_permission, assignment_created = (
                RolePermission.objects.get_or_create(
                    role=admin_role,
                    permission=permission,
                )
            )

            if assignment_created:
                assigned_permissions += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Assigned {permission_code} to Admin"
                    )
                )
            else:
                existing_assignments += 1

                self.stdout.write(
                    f"Admin already has {permission_code}"
                )

        # ---------------------------------------------------------
        # 4. Final summary.
        # ---------------------------------------------------------
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Company permission setup completed successfully."
            )
        )

        self.stdout.write(
            f"Permissions created: {created_permissions}"
        )

        self.stdout.write(
            f"Permissions already existing: {existing_permissions}"
        )

        self.stdout.write(
            f"Permissions newly assigned to Admin: {assigned_permissions}"
        )

        self.stdout.write(
            f"Admin assignments already existing: {existing_assignments}"
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Existing users, roles, and existing permission assignments "
                "were not deleted or recreated."
            )
        )