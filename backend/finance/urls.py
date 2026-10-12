from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ExpenseCategoryViewSet,
    ExpenseViewSet,
    ExpensePaymentViewSet,
)


router = DefaultRouter()

router.register(
    "expense-categories",
    ExpenseCategoryViewSet,
    basename="expense-category"
)

router.register(
    "expenses",
    ExpenseViewSet,
    basename="expense"
)

router.register(
    "expense-payments",
    ExpensePaymentViewSet,
    basename="expense-payment"
)


urlpatterns = [
    path("", include(router.urls)),
]