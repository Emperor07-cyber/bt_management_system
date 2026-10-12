from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import AssetAssignmentViewSet, AssetCategoryViewSet, AssetMaintenanceViewSet, AssetViewSet

maintenance_router = SimpleRouter()
maintenance_router.register("maintenance", AssetMaintenanceViewSet, basename="asset-maintenance")

category_router = SimpleRouter()
category_router.register("categories", AssetCategoryViewSet, basename="asset-category")

assignment_router = SimpleRouter()
assignment_router.register("assignments", AssetAssignmentViewSet, basename="asset-assignment")

asset_router = SimpleRouter()
asset_router.register("", AssetViewSet, basename="asset")

urlpatterns = [
    path("", include(category_router.urls)),
    path("<int:pk>/maintenance-history/", AssetViewSet.as_view({"get": "maintenance_history"}), name="asset-maintenance-history"),
    path("", include(maintenance_router.urls)),
    path("", include(assignment_router.urls)),
    path("", include(asset_router.urls)),
]
