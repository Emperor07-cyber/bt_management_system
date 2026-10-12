from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone
from openpyxl import load_workbook

from company.models import Location, Supplier
from .models import Category, Item, StockTransaction


ITEM_IMPORT_HEADERS = [
    "name",
    "description",
    "category",
    "brand",
    "model_number",
    "specifications",
    "supplier",
    "unit",
    "reorder_level",
    "minimum_stock",
    "is_active",
]

OPENING_STOCK_HEADERS = [
    "item_code",
    "location",
    "quantity",
    "reference",
    "notes",
]


def normalize(value):
    if value is None:
        return ""
    return str(value).strip()


def parse_bool(value, default=True):
    value = normalize(value).lower()

    if value in ("true", "yes", "1", "active"):
        return True

    if value in ("false", "no", "0", "inactive"):
        return False

    return default


def parse_integer(value, field_name):
    value = normalize(value)

    if not value:
        return None

    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a whole number.")

    return number


def parse_decimal(value, field_name):
    value = normalize(value)

    if not value:
        return None

    try:
        return Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"{field_name} must be a valid number.")


def find_category(value):
    value = normalize(value)

    if not value:
        return None

    if value.isdigit():
        category = Category.objects.filter(pk=int(value)).first()
    else:
        category = Category.objects.filter(name__iexact=value).first()

    if not category:
        raise ValueError(f"Category '{value}' was not found.")

    return category


def find_supplier(value):
    value = normalize(value)

    if not value:
        return None

    if value.isdigit():
        supplier = Supplier.objects.filter(pk=int(value)).first()
    else:
        supplier = Supplier.objects.filter(name__iexact=value).first()

    if not supplier:
        raise ValueError(f"Supplier '{value}' was not found.")

    return supplier


def find_location(value):
    value = normalize(value)

    if not value:
        raise ValueError("Location is required.")

    if value.isdigit():
        location = Location.objects.filter(pk=int(value)).first()
    else:
        location = Location.objects.filter(name__iexact=value).first()

    if not location:
        raise ValueError(f"Location '{value}' was not found.")

    return location


def validate_headers(headers, required_headers):
    normalized_headers = [normalize(header).lower() for header in headers]

    missing = [
        header
        for header in required_headers
        if header not in normalized_headers
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {', '.join(missing)}"
        )

    return normalized_headers


def read_excel(file):
    workbook = load_workbook(file, read_only=True, data_only=True)
    worksheet = workbook.active

    rows = list(worksheet.iter_rows(values_only=True))

    if not rows:
        raise ValueError("The Excel file is empty.")

    headers = [
        normalize(value).lower()
        for value in rows[0]
    ]

    data_rows = []

    for row_number, row in enumerate(rows[1:], start=2):
        if not any(normalize(value) for value in row):
            continue

        data = {}

        for index, header in enumerate(headers):
            if header:
                data[header] = row[index] if index < len(row) else None

        data_rows.append((row_number, data))

    return headers, data_rows


def validate_item_row(row_number, data):
    errors = []

    name = normalize(data.get("name"))
    category = normalize(data.get("category"))

    if not name:
        errors.append("name is required.")

    if not category:
        errors.append("category is required.")

    if item_code and Item.objects.filter(item_code__iexact=item_code).exists():
        errors.append(
            f"Item code '{item_code}' already exists."
        )

    try:
        if category:
            find_category(category)
    except ValueError as exc:
        errors.append(str(exc))

    supplier = normalize(data.get("supplier"))

    if supplier:
        try:
            find_supplier(supplier)
        except ValueError as exc:
            errors.append(str(exc))

    try:
        reorder_level = parse_integer(
            data.get("reorder_level"),
            "reorder_level",
        )

        if reorder_level is not None and reorder_level < 0:
            errors.append("reorder_level cannot be negative.")
    except ValueError as exc:
        errors.append(str(exc))

    try:
        minimum_stock = parse_integer(
            data.get("minimum_stock"),
            "minimum_stock",
        )

        if minimum_stock is not None and minimum_stock < 0:
            errors.append("minimum_stock cannot be negative.")
    except ValueError as exc:
        errors.append(str(exc))

    return errors


def validate_item_batch(batch, file):
    headers, rows = read_excel(file)

    validate_headers(headers, ITEM_IMPORT_HEADERS)

    batch.total_rows = len(rows)
    batch.valid_rows = 0
    batch.invalid_rows = 0

    batch.errors.all().delete()

    for row_number, data in rows:
        errors = validate_item_row(row_number, data)

        if errors:
            batch.invalid_rows += 1

            for message in errors:
                batch.errors.create(
                    row_number=row_number,
                    error_code="VALIDATION_ERROR",
                    message=message,
                    row_data={
                        key: normalize(value)
                        for key, value in data.items()
                    },
                )
        else:
            batch.valid_rows += 1

    batch.status = (
        batch.Status.VALIDATED
        if batch.invalid_rows == 0
        else batch.Status.FAILED
    )

    batch.save(
        update_fields=[
            "total_rows",
            "valid_rows",
            "invalid_rows",
            "status",
        ]
    )

    return batch


@transaction.atomic
def import_item_batch(batch, file):
    batch.status = batch.Status.IMPORTING
    batch.started_at = timezone.now()
    batch.save(update_fields=["status", "started_at"])

    headers, rows = read_excel(file)

    validate_headers(headers, ITEM_IMPORT_HEADERS)

    imported = 0

    for row_number, data in rows:
        item_code = normalize(data.get("item_code"))

        category = find_category(data.get("category"))
        supplier = find_supplier(data.get("supplier"))

        reorder_level = parse_integer(
            data.get("reorder_level"),
            "reorder_level",
        )

        minimum_stock = parse_integer(
            data.get("minimum_stock"),
            "minimum_stock",
        )

        item = Item.objects.create(
            name=normalize(data.get("name")),
            description=normalize(data.get("description")),
            category=category,
            brand=normalize(data.get("brand")),
            model_number=normalize(data.get("model_number")),
            specifications=normalize(data.get("specifications")),
            supplier=supplier,
            unit=normalize(data.get("unit")),
            reorder_level=reorder_level or 0,
            minimum_stock=minimum_stock or 0,
            is_active=parse_bool(data.get("is_active"), True),
        )

        imported += 1

    batch.imported_rows = imported
    batch.status = batch.Status.COMPLETED
    batch.completed_at = timezone.now()

    batch.save(
        update_fields=[
            "imported_rows",
            "status",
            "completed_at",
        ]
    )

    return batch


def validate_opening_stock_row(row_number, data):
    errors = []

    item_code = normalize(data.get("item_code"))
    location = normalize(data.get("location"))

    if not item_code:
        errors.append("item_code is required.")

    if not location:
        errors.append("location is required.")

    if item_code:
        item = Item.objects.filter(
            item_code__iexact=item_code
        ).first()

        if not item:
            errors.append(
                f"Item code '{item_code}' was not found."
            )
        elif not item.is_active:
            errors.append(
                f"Item '{item_code}' is inactive."
            )

    if location:
        try:
            find_location(location)
        except ValueError as exc:
            errors.append(str(exc))

    try:
        quantity = parse_integer(
            data.get("quantity"),
            "quantity",
        )

        if quantity is None:
            errors.append("quantity is required.")
        elif quantity <= 0:
            errors.append(
                "Opening stock quantity must be greater than zero."
            )
    except ValueError as exc:
        errors.append(str(exc))

    return errors


def validate_opening_stock_batch(batch, file):
    headers, rows = read_excel(file)

    validate_headers(headers, OPENING_STOCK_HEADERS)

    batch.total_rows = len(rows)
    batch.valid_rows = 0
    batch.invalid_rows = 0

    batch.errors.all().delete()

    for row_number, data in rows:
        errors = validate_opening_stock_row(
            row_number,
            data,
        )

        if errors:
            batch.invalid_rows += 1

            for message in errors:
                batch.errors.create(
                    row_number=row_number,
                    error_code="VALIDATION_ERROR",
                    message=message,
                    row_data={
                        key: normalize(value)
                        for key, value in data.items()
                    },
                )
        else:
            batch.valid_rows += 1

    batch.status = (
        batch.Status.VALIDATED
        if batch.invalid_rows == 0
        else batch.Status.FAILED
    )

    batch.save(
        update_fields=[
            "total_rows",
            "valid_rows",
            "invalid_rows",
            "status",
        ]
    )

    return batch


@transaction.atomic
def import_opening_stock_batch(batch, file):
    batch.status = batch.Status.IMPORTING
    batch.started_at = timezone.now()
    batch.save(update_fields=["status", "started_at"])

    headers, rows = read_excel(file)

    validate_headers(headers, OPENING_STOCK_HEADERS)

    imported = 0

    for row_number, data in rows:
        item_code = normalize(data.get("item_code"))
        location_value = normalize(data.get("location"))
        quantity = parse_integer(
            data.get("quantity"),
            "quantity",
        )

        item = Item.objects.filter(
            item_code__iexact=item_code
        ).first()

        if not item:
            raise ValueError(
                f"Item '{item_code}' was not found."
            )

        location = find_location(location_value)

        reference = normalize(data.get("reference"))

        if not reference:
            reference = (
                f"OPENING-{batch.id}-{row_number}"
            )

        StockTransaction.objects.create(
            item=item,
            transaction_type=StockTransaction.TransactionType.RECEIVED,
            quantity=quantity,
            reference=reference,
            notes=normalize(data.get("notes"))
            or "Opening stock import.",
            location=location,
            created_by=batch.uploaded_by,
        )

        imported += 1

    batch.imported_rows = imported
    batch.status = batch.Status.COMPLETED
    batch.completed_at = timezone.now()

    batch.save(
        update_fields=[
            "imported_rows",
            "status",
            "completed_at",
        ]
    )

    return batch