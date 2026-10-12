from django.db import transaction
from django.db.models import Sum
from rest_framework import viewsets

from authentication.permissions import RoleBasedPermission

from .models import ExpenseCategory, Expense, ExpensePayment
from .serializers import (
    ExpenseCategorySerializer,
    ExpenseSerializer,
    ExpensePaymentSerializer,
)


class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    queryset = ExpenseCategory.objects.all()
    serializer_class = ExpenseCategorySerializer
    permission_classes = [RoleBasedPermission]


class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer
    permission_classes = [RoleBasedPermission]


class ExpensePaymentViewSet(viewsets.ModelViewSet):
    queryset = ExpensePayment.objects.all()
    serializer_class = ExpensePaymentSerializer
    permission_classes = [RoleBasedPermission]

    def perform_destroy(self, instance):
        expense = instance.expense

        with transaction.atomic():
            instance.delete()

            if expense.status == Expense.Status.CANCELLED:
                return

            total_paid = (
                expense.payments.aggregate(total=Sum("amount"))["total"]
                or 0
            )

            if total_paid >= expense.amount:
                expense.status = Expense.Status.PAID
            elif total_paid > 0:
                expense.status = Expense.Status.APPROVED
            else:
                expense.status = Expense.Status.PENDING

            expense.save(update_fields=["status"])