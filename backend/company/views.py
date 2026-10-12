from django.db import transaction
from django.db.models import Q

from rest_framework import status, viewsets
from rest_framework.response import Response

from authentication.permissions import RoleBasedPermission

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


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.select_related("manager").all()
    serializer_class = DepartmentSerializer
    permission_classes = [RoleBasedPermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        is_active = self.request.query_params.get("is_active")
        search = self.request.query_params.get("search")

        if is_active in {"true", "false"}:
            queryset = queryset.filter(is_active=(is_active == "true"))

        if search:
            queryset = queryset.filter(
                Q(department_code__icontains=search)
                | Q(name__icontains=search)
            )

        return queryset


class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.select_related("parent").all()
    serializer_class = LocationSerializer
    permission_classes = [RoleBasedPermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        is_active = self.request.query_params.get("is_active")
        search = self.request.query_params.get("search")
        parent = self.request.query_params.get("parent")

        if is_active in {"true", "false"}:
            queryset = queryset.filter(is_active=(is_active == "true"))

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(address__icontains=search)
            )

        if parent:
            queryset = queryset.filter(parent_id=parent)

        return queryset


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.select_related(
        "department",
        "location",
    ).prefetch_related("module_affiliations")
    serializer_class = EmployeeSerializer
    permission_classes = [RoleBasedPermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        status_value = self.request.query_params.get("status")
        department = self.request.query_params.get("department")
        location = self.request.query_params.get("location")
        module = self.request.query_params.get("module")
        search = self.request.query_params.get("search")

        if status_value in {Employee.Status.ACTIVE, Employee.Status.INACTIVE}:
            queryset = queryset.filter(status=status_value)

        if department:
            queryset = queryset.filter(department_id=department)

        if location:
            queryset = queryset.filter(location_id=location)

        if module:
            queryset = queryset.filter(
                module_affiliations__module=module,
                module_affiliations__is_active=True,
            )

        if search:
            queryset = queryset.filter(
                Q(employee_number__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
                | Q(phone__icontains=search)
            )

        return queryset.distinct()

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        employee = self.get_object()

        if employee.status == Employee.Status.INACTIVE:
            EmployeeModuleAffiliation.objects.filter(
                employee=employee,
                is_active=True,
            ).update(is_active=False)

        return response

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        response = super().partial_update(request, *args, **kwargs)
        employee = self.get_object()

        if employee.status == Employee.Status.INACTIVE:
            EmployeeModuleAffiliation.objects.filter(
                employee=employee,
                is_active=True,
            ).update(is_active=False)

        return response


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [RoleBasedPermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        is_active = self.request.query_params.get("is_active")
        search = self.request.query_params.get("search")

        if is_active in {"true", "false"}:
            queryset = queryset.filter(is_active=(is_active == "true"))

        if search:
            queryset = queryset.filter(
                Q(supplier_code__icontains=search)
                | Q(name__icontains=search)
                | Q(contact_person__icontains=search)
            )

        return queryset


class CompanySettingViewSet(viewsets.ModelViewSet):
    queryset = CompanySetting.objects.all()
    serializer_class = CompanySettingSerializer
    permission_classes = [RoleBasedPermission]

    def create(self, request, *args, **kwargs):
        if CompanySetting.objects.exists():
            from rest_framework.exceptions import ValidationError

            raise ValidationError({
                "detail": (
                    "Company settings already exist. Only one company "
                    "setting record is allowed."
                )
            })

        return super().create(request, *args, **kwargs)


class EmployeeModuleAffiliationViewSet(viewsets.ModelViewSet):
    queryset = EmployeeModuleAffiliation.objects.select_related(
        "employee"
    ).all()
    serializer_class = EmployeeModuleAffiliationSerializer
    permission_classes = [RoleBasedPermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        employee = self.request.query_params.get("employee")
        module = self.request.query_params.get("module")
        is_active = self.request.query_params.get("is_active")

        if employee:
            queryset = queryset.filter(employee_id=employee)

        if module:
            queryset = queryset.filter(module=module)

        if is_active in {"true", "false"}:
            queryset = queryset.filter(is_active=(is_active == "true"))

        return queryset