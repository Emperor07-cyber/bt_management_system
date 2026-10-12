from django.db.models import Q, Sum
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.permissions import RoleBasedPermission

from assets.models import Asset
from inventory.models import Item
from fleet.models import Vehicle
from procurement.models import PurchaseOrder, SupplierInvoice
from finance.models import Expense


def has_module_read(user, module):
    return RoleBasedPermission.user_has_module_permission(
        user, module, "READ"
    )


def can_view_financial_data(user):
    return RoleBasedPermission.is_financial_data_role(user)


class DashboardView(APIView):
    permission_classes = [RoleBasedPermission]

    def get(self, request):
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        response = {
            "filters": {
                "start_date": start_date,
                "end_date": end_date,
            },
            "inventory": None,
            "fleet": None,
            "procurement": None,
            "finance": None,
            "assets": None,
            "recent_activity": [],
        }

        if has_module_read(request.user, "ASSET"):
            response["assets"] = {
                "total_assets": Asset.objects.count(),
            }

        if has_module_read(request.user, "INVENTORY"):
            items = Item.objects.all()
            response["inventory"] = {
                "total_items": items.count(),
                "low_stock_items": sum(
                    1 for item in items if item.stock_status == "LOW_STOCK"
                ),
                "out_of_stock_items": sum(
                    1
                    for item in items
                    if item.stock_status == "OUT_OF_STOCK"
                ),
            }

        if has_module_read(request.user, "FLEET"):
            response["fleet"] = {
                "total_vehicles": Vehicle.objects.count(),
                "available_vehicles": Vehicle.objects.filter(
                    status="AVAILABLE"
                ).count(),
                "assigned_vehicles": Vehicle.objects.filter(
                    status="ASSIGNED"
                ).count(),
            }

        if has_module_read(request.user, "PROCUREMENT"):
            response["procurement"] = {
                "total_purchase_orders": PurchaseOrder.objects.count(),
                "total_supplier_invoices": SupplierInvoice.objects.count(),
            }

        if can_view_financial_data(request.user):
            expenses = Expense.objects.all()
            if start_date:
                expenses = expenses.filter(expense_date__gte=start_date)
            if end_date:
                expenses = expenses.filter(expense_date__lte=end_date)

            response["finance"] = {
                "total_expenses": expenses.aggregate(
                    total=Sum("amount")
                )["total"] or 0,
                "paid_expenses": expenses.filter(
                    status=Expense.Status.PAID
                ).aggregate(total=Sum("amount"))["total"] or 0,
                "pending_expenses": expenses.filter(
                    status=Expense.Status.PENDING
                ).aggregate(total=Sum("amount"))["total"] or 0,
            }

        recent_activity = []

        if has_module_read(request.user, "ASSET"):
            for asset in Asset.objects.order_by("-created_at")[:3]:
                recent_activity.append({
                    "type": "asset",
                    "title": f"Asset added: {asset}",
                    "date": asset.created_at,
                })

        if has_module_read(request.user, "INVENTORY"):
            for item in Item.objects.order_by("-created_at")[:3]:
                recent_activity.append({
                    "type": "inventory",
                    "title": f"Inventory item added: {item.name}",
                    "date": item.created_at,
                })

        if has_module_read(request.user, "FLEET"):
            for vehicle in Vehicle.objects.order_by("-created_at")[:3]:
                recent_activity.append({
                    "type": "fleet",
                    "title": f"Vehicle added: {vehicle.vehicle_code}",
                    "date": vehicle.created_at,
                })

        if has_module_read(request.user, "PROCUREMENT"):
            for order in PurchaseOrder.objects.order_by("-created_at")[:3]:
                recent_activity.append({
                    "type": "procurement",
                    "title": f"Purchase order: {order.order_number}",
                    "date": order.created_at,
                })

        if can_view_financial_data(request.user):
            for expense in Expense.objects.order_by("-created_at")[:3]:
                recent_activity.append({
                    "type": "finance",
                    "title": f"Expense recorded: {expense.expense_number}",
                    "date": expense.created_at,
                })

        recent_activity.sort(
            key=lambda activity: activity["date"],
            reverse=True,
        )
        response["recent_activity"] = recent_activity[:8]

        return Response(response)


class GlobalSearchView(APIView):
    permission_classes = [RoleBasedPermission]

    def get(self, request):
        query = request.query_params.get("q", "").strip()

        if not query:
            return Response({"query": "", "results": []})

        results = []

        if has_module_read(request.user, "ASSET"):
            assets = Asset.objects.filter(
                Q(asset_code__icontains=query) | Q(name__icontains=query)
            )[:5]
            for asset in assets:
                results.append({
                    "type": "asset",
                    "title": str(asset),
                    "subtitle": "Asset",
                    "id": asset.id,
                })

        if has_module_read(request.user, "INVENTORY"):
            items = Item.objects.filter(
                Q(item_code__icontains=query)
                | Q(name__icontains=query)
                | Q(brand__icontains=query)
                | Q(model_number__icontains=query)
            )[:5]
            for item in items:
                results.append({
                    "type": "inventory",
                    "title": item.name,
                    "subtitle": f"Inventory • {item.item_code}",
                    "id": item.id,
                })

        if has_module_read(request.user, "FLEET"):
            vehicles = Vehicle.objects.filter(
                Q(vehicle_code__icontains=query)
                | Q(registration_number__icontains=query)
                | Q(make__icontains=query)
                | Q(model__icontains=query)
            )[:5]
            for vehicle in vehicles:
                results.append({
                    "type": "fleet",
                    "title": f"{vehicle.make} {vehicle.model}",
                    "subtitle": f"Fleet • {vehicle.registration_number}",
                    "id": vehicle.id,
                })

        if has_module_read(request.user, "PROCUREMENT"):
            orders = PurchaseOrder.objects.filter(
                Q(order_number__icontains=query) | Q(notes__icontains=query)
            )[:5]
            for order in orders:
                results.append({
                    "type": "procurement",
                    "title": order.order_number,
                    "subtitle": "Purchase Order",
                    "id": order.id,
                })

        if can_view_financial_data(request.user):
            expenses = Expense.objects.filter(
                Q(expense_number__icontains=query)
                | Q(description__icontains=query)
                | Q(notes__icontains=query)
            )[:5]
            for expense in expenses:
                results.append({
                    "type": "finance",
                    "title": expense.expense_number,
                    "subtitle": f"Expense • {expense.description}",
                    "id": expense.id,
                })

        return Response({
            "query": query,
            "results": results[:20],
        })


class NotificationsView(APIView):
    permission_classes = [RoleBasedPermission]

    def get(self, request):
        notifications = []

        if has_module_read(request.user, "INVENTORY"):
            low_stock_items = Item.objects.filter(is_active=True)
            for item in low_stock_items:
                if item.stock_status in ["LOW_STOCK", "OUT_OF_STOCK"]:
                    notifications.append({
                        "type": "inventory",
                        "level": (
                            "danger"
                            if item.stock_status == "OUT_OF_STOCK"
                            else "warning"
                        ),
                        "title": (
                            f"{item.name} is "
                            f"{item.stock_status.replace('_', ' ').title()}"
                        ),
                        "message": (
                            f"Current stock: {item.current_stock}. "
                            f"Reorder level: {item.reorder_level}."
                        ),
                        "id": item.id,
                    })

        if can_view_financial_data(request.user):
            pending_expenses = Expense.objects.filter(
                status=Expense.Status.PENDING
            ).order_by("-expense_date")[:10]
            for expense in pending_expenses:
                notifications.append({
                    "type": "finance",
                    "level": "warning",
                    "title": f"Pending expense: {expense.expense_number}",
                    "message": (
                        f"{expense.description} — "
                        f"₦{expense.amount:,.2f}"
                    ),
                    "id": expense.id,
                })

        if has_module_read(request.user, "FLEET"):
            maintenance_vehicles = Vehicle.objects.filter(
                status=Vehicle.Status.MAINTENANCE
            )[:10]
            for vehicle in maintenance_vehicles:
                notifications.append({
                    "type": "fleet",
                    "level": "warning",
                    "title": (
                        f"Vehicle in maintenance: "
                        f"{vehicle.vehicle_code}"
                    ),
                    "message": (
                        f"{vehicle.make} {vehicle.model} "
                        f"({vehicle.registration_number})"
                    ),
                    "id": vehicle.id,
                })

        if has_module_read(request.user, "PROCUREMENT"):
            pending_orders = PurchaseOrder.objects.filter(
                status="PENDING"
            ).order_by("-order_date")[:10]
            for order in pending_orders:
                notifications.append({
                    "type": "procurement",
                    "level": "info",
                    "title": f"Pending purchase order: {order.order_number}",
                    "message": "Purchase order requires attention.",
                    "id": order.id,
                })

        return Response({
            "count": len(notifications),
            "notifications": notifications[:20],
        })
