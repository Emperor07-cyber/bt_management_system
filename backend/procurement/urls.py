from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    PurchaseOrderViewSet,
    PurchaseOrderItemViewSet,
    GoodsReceiptViewSet,
    GoodsReceiptItemViewSet,
    SupplierInvoiceViewSet,
    SupplierPaymentViewSet,
)

router = DefaultRouter()

router.register(
    "purchase-orders",
    PurchaseOrderViewSet,
    basename="purchase-order"
)

router.register(
    "purchase-order-items",
    PurchaseOrderItemViewSet,
    basename="purchase-order-item"
)

router.register(
    "goods-receipts",
    GoodsReceiptViewSet,
    basename="goods-receipt"
)

router.register(
    "supplier-invoices",
    SupplierInvoiceViewSet,
    basename="supplier-invoice"
)

router.register(
    "supplier-payments",
    SupplierPaymentViewSet,
    basename="supplier-payment"
)

router.register(
    "goods-receipt-items",
    GoodsReceiptItemViewSet,
    basename="goods-receipt-item"
)

urlpatterns = [
    path("", include(router.urls)),
]