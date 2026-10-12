from rest_framework.test import APITestCase

from authentication.models import Permission, Role, RolePermission, User, UserRole
from company.models import Supplier
from inventory.models import Category, Item, StockTransaction
from .models import (
    PurchaseOrder, PurchaseOrderItem, GoodsReceipt, GoodsReceiptItem,
    SupplierInvoice, SupplierPayment,
)


class ProcurementAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("procurement_test", password="pass1234")
        role = Role.objects.create(name="Procurement Test Role")
        for action in ("READ", "CREATE", "UPDATE", "DELETE"):
            permission = Permission.objects.create(permission_code=f"PROCUREMENT_{action}")
            RolePermission.objects.create(role=role, permission=permission)
        UserRole.objects.create(user=self.user, role=role)
        self.client.force_authenticate(self.user)
        self.supplier = Supplier.objects.create(supplier_code="SUP-PRO", name="Procurement Supplier")
        self.category = Category.objects.create(name="Procurement Hardware")
        self.item = Item.objects.create(item_code="ITM-PRO", name="Cable", category=self.category)
        self.order = PurchaseOrder.objects.create(
            order_number="PO-001", supplier=self.supplier, order_date="2026-09-10"
        )

    def test_purchase_order_crud(self):
        response = self.client.post("/api/v1/procurement/purchase-orders/", {
            "order_number": "PO-002", "supplier": self.supplier.id, "order_date": "2026-09-10",
        }, format="json")
        self.assertEqual(response.status_code, 201)
        order_id = response.data["id"]
        response = self.client.patch(f"/api/v1/procurement/purchase-orders/{order_id}/", {"status": "APPROVED"}, format="json")
        self.assertEqual(response.status_code, 200)
        response = self.client.delete(f"/api/v1/procurement/purchase-orders/{order_id}/")
        self.assertEqual(response.status_code, 204)

    def test_purchase_order_item_total_price(self):
        response = self.client.post("/api/v1/procurement/purchase-order-items/", {
            "purchase_order": self.order.id, "item": self.item.id,
            "quantity": 4, "unit_price": "2500.00",
        }, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(str(response.data["total_price"]), "10000.00")

    def test_goods_receipt_item_creates_received_stock_transaction(self):
        PurchaseOrderItem.objects.create(
            purchase_order=self.order,
            item=self.item,
            quantity=12,
            unit_price="1000.00",
        )

        receipt = GoodsReceipt.objects.create(
            receipt_number="GR-001",
            purchase_order=self.order,
            receipt_date="2026-09-10",
        )

        response = self.client.post(
            "/api/v1/procurement/goods-receipt-items/",
            {
                "goods_receipt": receipt.id,
                "item": self.item.id,
                "quantity_received": 12,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
            response.data,
        )

        self.assertTrue(
            StockTransaction.objects.filter(
                item=self.item,
                transaction_type="RECEIVED",
                quantity=12,
                reference="GR-001",
            ).exists()
        )

        self.item.refresh_from_db()
        self.assertEqual(self.item.current_stock, 12)

    def test_supplier_invoice_payment_updates_status(self):
        invoice = SupplierInvoice.objects.create(
            invoice_number="INV-001", supplier=self.supplier,
            purchase_order=self.order, invoice_date="2026-09-10", amount="50000.00"
        )
        response = self.client.post("/api/v1/procurement/supplier-payments/", {
            "invoice": invoice.id, "payment_date": "2026-09-10",
            "amount": "50000.00", "payment_method": "BANK_TRANSFER",
        }, format="json")
        self.assertEqual(response.status_code, 201)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, SupplierInvoice.Status.PAID)

    def test_supplier_invoice_partial_payment_sets_partial(self):
        invoice = SupplierInvoice.objects.create(
            invoice_number="INV-002", supplier=self.supplier,
            purchase_order=self.order, invoice_date="2026-09-10", amount="50000.00"
        )
        response = self.client.post("/api/v1/procurement/supplier-payments/", {
            "invoice": invoice.id, "payment_date": "2026-09-10",
            "amount": "10000.00", "payment_method": "CASH",
        }, format="json")
        self.assertEqual(
    response.status_code,
    201,
    response.data,
)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, SupplierInvoice.Status.PARTIAL)

    def test_duplicate_purchase_order_number_is_rejected(self):
        response = self.client.post("/api/v1/procurement/purchase-orders/", {
            "order_number": "PO-001", "supplier": self.supplier.id, "order_date": "2026-09-10",
        }, format="json")
        self.assertEqual(response.status_code, 400)

    def test_unauthenticated_procurement_request_is_denied(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/v1/procurement/purchase-orders/")
        self.assertIn(response.status_code, (401, 403))
