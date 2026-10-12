from django.urls import include, path
from rest_framework.routers import SimpleRouter
from .views import (
    CategoryViewSet,
    InventoryUnitViewSet,
    ItemViewSet,
    StockTransactionViewSet,
    StockTransferViewSet,
    StocktakeViewSet,
    StocktakeLineViewSet,
)

router = SimpleRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("items", ItemViewSet, basename="item")
router.register("units", InventoryUnitViewSet, basename="inventory-unit")
router.register("transactions", StockTransactionViewSet, basename="stock-transaction")
router.register("transfers", StockTransferViewSet, basename="stock-transfer")
router.register("stocktakes", StocktakeViewSet, basename="stocktake")
router.register("stocktake-lines", StocktakeLineViewSet, basename="stocktake-line")

urlpatterns = [
    path("", include(router.urls)),
]
