from django.db.models.deletion import ProtectedError
from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.response import Response

from .models import (
    PurchaseOrder,
    PurchaseOrderItem,
    GoodsReceipt,
    GoodsReceiptItem,
    SupplierInvoice,
    SupplierPayment,
)

from .serializers import (
    PurchaseOrderSerializer,
    PurchaseOrderItemSerializer,
    GoodsReceiptSerializer,
    GoodsReceiptItemSerializer,
    SupplierInvoiceSerializer,
    SupplierPaymentSerializer,
)

from authentication.permissions import RoleBasedPermission


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [RoleBasedPermission]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        try:
            self.perform_destroy(instance)

        except ProtectedError:
            return Response(
                {
                    "detail": (
                        "This purchase order cannot be deleted "
                        "because it has related goods receipts "
                        "or supplier invoices."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


class PurchaseOrderItemViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrderItem.objects.all()
    serializer_class = PurchaseOrderItemSerializer
    permission_classes = [RoleBasedPermission]


class GoodsReceiptViewSet(viewsets.ModelViewSet):
    queryset = GoodsReceipt.objects.all()
    serializer_class = GoodsReceiptSerializer
    permission_classes = [RoleBasedPermission]


class GoodsReceiptItemViewSet(viewsets.ModelViewSet):
    queryset = GoodsReceiptItem.objects.all()
    serializer_class = GoodsReceiptItemSerializer
    permission_classes = [RoleBasedPermission]


class SupplierInvoiceViewSet(viewsets.ModelViewSet):
    queryset = SupplierInvoice.objects.all()
    serializer_class = SupplierInvoiceSerializer
    permission_classes = [RoleBasedPermission]


class SupplierPaymentViewSet(viewsets.ModelViewSet):
    queryset = SupplierPayment.objects.all()
    serializer_class = SupplierPaymentSerializer
    permission_classes = [RoleBasedPermission]

    def perform_destroy(self, instance):
        invoice = instance.invoice

        with transaction.atomic():
            instance.delete()

            if invoice.status != SupplierInvoice.Status.CANCELLED:
                if invoice.total_paid >= invoice.amount:
                    invoice.status = SupplierInvoice.Status.PAID
                elif invoice.total_paid > 0:
                    invoice.status = SupplierInvoice.Status.PARTIAL
                else:
                    invoice.status = SupplierInvoice.Status.UNPAID

                invoice.save(update_fields=["status"])