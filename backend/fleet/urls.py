from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import (
    VehicleViewSet,
    VehicleAssignmentViewSet,
    VehicleMaintenanceViewSet,
)


router = DefaultRouter()

router.register(
    "vehicles",
    VehicleViewSet,
    basename="vehicle"
)

router.register(
    "assignments",
    VehicleAssignmentViewSet,
    basename="vehicle-assignment"
)

router.register(
    "maintenance",
    VehicleMaintenanceViewSet,
    basename="vehicle-maintenance"
)

urlpatterns = [
    path("", include(router.urls)),
]
