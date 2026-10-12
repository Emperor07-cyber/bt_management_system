from django.urls import include, path

from rest_framework.routers import SimpleRouter

from .views import (
    CompanySettingViewSet,
    DepartmentViewSet,
    EmployeeModuleAffiliationViewSet,
    EmployeeViewSet,
    LocationViewSet,
    SupplierViewSet,
)


router = SimpleRouter()

router.register(
    "departments",
    DepartmentViewSet,
    basename="department",
)

router.register(
    "locations",
    LocationViewSet,
    basename="location",
)

router.register(
    "employees",
    EmployeeViewSet,
    basename="employee",
)

router.register(
    "suppliers",
    SupplierViewSet,
    basename="supplier",
)

router.register(
    "settings",
    CompanySettingViewSet,
    basename="company-setting",
)

router.register(
    "employee-affiliations",
    EmployeeModuleAffiliationViewSet,
    basename="employee-affiliation",
)


urlpatterns = [
    path("", include(router.urls)),
]