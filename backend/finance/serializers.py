from django.db import transaction
from django.db.models import Sum
from rest_framework import serializers

from .models import (
    ExpenseCategory,
    Expense,
    ExpensePayment,
)


class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = "__all__"

    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Category name cannot be empty."
            )

        return value


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = "__all__"

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Expense amount must be greater than zero."
            )
        return value

    def validate(self, attrs):
        category = attrs.get(
            "category",
            getattr(self.instance, "category", None),
        )

        employee = attrs.get(
            "employee",
            getattr(self.instance, "employee", None),
        )

        if category is not None and not category.is_active:
            raise serializers.ValidationError({
                "category": (
                    "Expenses can only use active expense categories."
                )
            })

        if employee is not None and employee.status != "ACTIVE":
            raise serializers.ValidationError({
                "employee": (
                    "An expense can only be assigned to an active employee."
                )
            })

        return attrs


class ExpensePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpensePayment
        fields = "__all__"

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Payment amount must be greater than zero."
            )
        return value

    def validate(self, attrs):
        expense = attrs.get(
            "expense",
            getattr(self.instance, "expense", None),
        )

        if expense is None:
            return attrs

        if expense.status == Expense.Status.CANCELLED:
            raise serializers.ValidationError({
                "expense": (
                    "Payments cannot be made against a cancelled expense."
                )
            })

        amount = attrs.get(
            "amount",
            getattr(self.instance, "amount", 0),
        )

        existing_paid = (
            expense.payments.aggregate(
                total=Sum("amount")
            )["total"] or 0
        )

        # When updating an existing payment, exclude its old amount.
        if self.instance:
            existing_paid -= self.instance.amount

        balance = expense.amount - existing_paid

        if amount > balance:
            raise serializers.ValidationError({
                "amount": (
                    f"Payment cannot exceed the expense balance "
                    f"({balance})."
                )
            })

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        expense = (
            Expense.objects
            .select_for_update()
            .get(pk=validated_data["expense"].pk)
        )

        if expense.status == Expense.Status.CANCELLED:
            raise serializers.ValidationError({
                "expense": (
                    "Payments cannot be made against a cancelled expense."
                )
            })

        amount = validated_data["amount"]

        if amount > expense.balance:
            raise serializers.ValidationError({
                "amount": (
                    f"Payment cannot exceed the expense balance "
                    f"({expense.balance})."
                )
            })

        payment = ExpensePayment.objects.create(
            **validated_data
        )

        self._update_expense_status(expense)

        return payment

    @transaction.atomic
    def update(self, instance, validated_data):
        old_expense = instance.expense

        payment = super().update(
            instance,
            validated_data,
        )

        expense_ids = {
            old_expense.pk,
            payment.expense_id,
        }

        for expense_id in expense_ids:
            expense = (
                Expense.objects
                .select_for_update()
                .get(pk=expense_id)
            )

            self._update_expense_status(expense)

        return payment

    @staticmethod
    def _update_expense_status(expense):
        if expense.status == Expense.Status.CANCELLED:
            return

        total_paid = (
            expense.payments.aggregate(
                total=Sum("amount")
            )["total"] or 0
        )

        if total_paid >= expense.amount:
            expense.status = Expense.Status.PAID
        elif total_paid > 0:
            expense.status = Expense.Status.APPROVED
        else:
            # Do not force an existing status to PENDING.
            if expense.status == Expense.Status.PAID:
                expense.status = Expense.Status.APPROVED

        expense.save(update_fields=["status"])