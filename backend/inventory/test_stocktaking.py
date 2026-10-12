from rest_framework.test import APITestCase

from authentication.models import User
from company.models import Location
from inventory.models import Category, Item, StockTransaction, Stocktake


class StocktakingAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="stocktake_test_admin",
            password="TestPass123!",
        )

        self.client.force_authenticate(user=self.user)

        self.location = Location.objects.create(
            location_code="ST-LOC-01",
            name="Main Store",
            parent=None,
            is_active=True,
        )

        self.category = Category.objects.create(
            name="Stocktake Test"
        )

        self.item = Item.objects.create(
            item_code="STK-ITEM-01",
            name="Test Item",
            category=self.category,
        )

        StockTransaction.objects.create(
            item=self.item,
            transaction_type=StockTransaction.TransactionType.RECEIVED,
            quantity=10,
            location=self.location,
            reference="OPEN-001",
            created_by=self.user,
        )

    def create_stocktake(self):
        response = self.client.post(
            "/api/v1/inventory/stocktakes/",
            {
                "reference": "STK-TEST-001",
                "location": self.location.id,
                "notes": "Test count",
                "item_ids": [self.item.id],
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
            response.data,
        )

        return response.data

    def test_create_snapshots_location_stock(self):
        data = self.create_stocktake()

        self.assertEqual(data["total_lines"], 1)

        self.assertEqual(
            data["lines"][0]["system_quantity"],
            10,
        )

        self.assertEqual(
            data["lines"][0]["counted_quantity"],
            None,
        )

    def test_confirm_positive_variance_creates_adjustment(self):
        data = self.create_stocktake()

        line_id = data["lines"][0]["id"]

        update = self.client.patch(
            f"/api/v1/inventory/stocktake-lines/{line_id}/",
            {
                "counted_quantity": 12,
            },
            format="json",
        )

        self.assertEqual(
            update.status_code,
            200,
            update.data,
        )

        confirm = self.client.post(
            f"/api/v1/inventory/stocktakes/{data['id']}/confirm/",
            {},
            format="json",
        )

        self.assertEqual(
            confirm.status_code,
            200,
            confirm.data,
        )

        self.assertEqual(
            confirm.data["status"],
            Stocktake.Status.COMPLETED,
        )

        self.item.refresh_from_db()

        self.assertEqual(
            self.item.current_stock,
            12,
        )

        self.assertEqual(
            StockTransaction.objects.filter(
                reference="STK-TEST-001-STK-ITEM-01",
                transaction_type=(
                    StockTransaction.TransactionType.ADJUSTMENT
                ),
                quantity=2,
            ).count(),
            1,
        )

    def test_confirm_zero_variance_creates_no_adjustment(self):
        data = self.create_stocktake()

        line_id = data["lines"][0]["id"]

        update = self.client.patch(
            f"/api/v1/inventory/stocktake-lines/{line_id}/",
            {
                "counted_quantity": 10,
            },
            format="json",
        )

        self.assertEqual(
            update.status_code,
            200,
            update.data,
        )

        confirm = self.client.post(
            f"/api/v1/inventory/stocktakes/{data['id']}/confirm/",
            {},
            format="json",
        )

        self.assertEqual(
            confirm.status_code,
            200,
            confirm.data,
        )

        self.item.refresh_from_db()

        self.assertEqual(
            self.item.current_stock,
            10,
        )

        self.assertFalse(
            StockTransaction.objects.filter(
                reference="STK-TEST-001-STK-ITEM-01",
                transaction_type=(
                    StockTransaction.TransactionType.ADJUSTMENT
                ),
            ).exists()
        )

    def test_confirm_requires_all_lines_to_be_counted(self):
        data = self.create_stocktake()

        response = self.client.post(
            f"/api/v1/inventory/stocktakes/{data['id']}/confirm/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "counted_quantity",
            response.data,
        )

    def test_confirmation_is_blocked_if_system_stock_changed(self):
        data = self.create_stocktake()

        line_id = data["lines"][0]["id"]

        update = self.client.patch(
            f"/api/v1/inventory/stocktake-lines/{line_id}/",
            {
                "counted_quantity": 11,
            },
            format="json",
        )

        self.assertEqual(
            update.status_code,
            200,
            update.data,
        )

        StockTransaction.objects.create(
            item=self.item,
            transaction_type=(
                StockTransaction.TransactionType.RECEIVED
            ),
            quantity=1,
            location=self.location,
            reference="BETWEEN-001",
            created_by=self.user,
        )

        response = self.client.post(
            f"/api/v1/inventory/stocktakes/{data['id']}/confirm/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "stock_changed",
            response.data,
        )

        self.assertEqual(
            Stocktake.objects.get(pk=data["id"]).status,
            Stocktake.Status.DRAFT,
        )

    def test_duplicate_confirmation_is_rejected(self):
        data = self.create_stocktake()

        line_id = data["lines"][0]["id"]

        update = self.client.patch(
            f"/api/v1/inventory/stocktake-lines/{line_id}/",
            {
                "counted_quantity": 10,
            },
            format="json",
        )

        self.assertEqual(
            update.status_code,
            200,
            update.data,
        )

        first = self.client.post(
            f"/api/v1/inventory/stocktakes/{data['id']}/confirm/",
            {},
            format="json",
        )

        self.assertEqual(
            first.status_code,
            200,
            first.data,
        )

        second = self.client.post(
            f"/api/v1/inventory/stocktakes/{data['id']}/confirm/",
            {},
            format="json",
        )

        self.assertEqual(
            second.status_code,
            400,
        )