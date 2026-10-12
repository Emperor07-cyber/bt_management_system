from django.db import transaction
from django.utils import timezone
from openpyxl import load_workbook

from company.models import Supplier
from .models import Vehicle


VEHICLE_IMPORT_HEADERS = [
    "registration_number",
    "make",
    "model",
    "year",
    "color",
    "vin",
    "engine_number",
    "vehicle_type",
    "fuel_type",
    "status",
    "purchase_date",
    "purchase_cost",
    "supplier",
    "current_mileage",
    "notes",
]


def normalize(value):
    if value is None:
        return ""
    return str(value).strip()


def parse_integer(value, field_name):
    value = normalize(value)

    if not value:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a whole number.")


def parse_decimal(value, field_name):
    value = normalize(value)

    if not value:
        return None

    try:
        from decimal import Decimal
        return Decimal(value)
    except Exception:
        raise ValueError(f"{field_name} must be a valid number.")


def parse_date(value, field_name):
    if not value:
        return None

    if hasattr(value, "date"):
        return value.date()

    value = normalize(value)

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            from datetime import datetime
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    raise ValueError(
        f"{field_name} must use YYYY-MM-DD format."
    )


def find_supplier(value):
    value = normalize(value)

    if not value:
        return None

    if value.isdigit():
        supplier = Supplier.objects.filter(
            pk=int(value)
        ).first()
    else:
        supplier = Supplier.objects.filter(
            name__iexact=value
        ).first()

    if not supplier:
        raise ValueError(
            f"Supplier '{value}' was not found."
        )

    return supplier


def read_vehicle_excel(file):
    workbook = load_workbook(
        file,
        read_only=True,
        data_only=True,
    )

    worksheet = workbook.active
    rows = list(
        worksheet.iter_rows(values_only=True)
    )

    if not rows:
        raise ValueError(
            "The Excel file is empty."
        )

    headers = [
        normalize(value).lower()
        for value in rows[0]
    ]

    data_rows = []

    for row_number, row in enumerate(
        rows[1:],
        start=2,
    ):
        if not any(normalize(value) for value in row):
            continue

        data = {}

        for index, header in enumerate(headers):
            if header:
                data[header] = (
                    row[index]
                    if index < len(row)
                    else None
                )

        data_rows.append(
            (row_number, data)
        )

    return headers, data_rows


def validate_headers(headers):
    missing = [
        header
        for header in VEHICLE_IMPORT_HEADERS
        if header not in headers
    ]

    if missing:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(missing)
        )


def validate_vehicle_row(row_number, data):
    errors = []

    registration_number = normalize(
        data.get("registration_number")
    )

    if not registration_number:
        errors.append(
            "registration_number is required."
        )

    if not normalize(data.get("make")):
        errors.append("make is required.")

    if not normalize(data.get("model")):
        errors.append("model is required.")

    if registration_number:
        if Vehicle.objects.filter(
            registration_number__iexact=
            registration_number
        ).exists():
            errors.append(
                f"Vehicle '{registration_number}' "
                "already exists."
            )

    try:
        year = parse_integer(
            data.get("year"),
            "year",
        )

        if year is not None and (
            year < 1900 or year > 2100
        ):
            errors.append(
                "year must be between 1900 and 2100."
            )
    except ValueError as exc:
        errors.append(str(exc))

    try:
        mileage = parse_integer(
            data.get("current_mileage"),
            "current_mileage",
        )

        if mileage is not None and mileage < 0:
            errors.append(
                "current_mileage cannot be negative."
            )
    except ValueError as exc:
        errors.append(str(exc))

    try:
        cost = parse_decimal(
            data.get("purchase_cost"),
            "purchase_cost",
        )

        if cost is not None and cost < 0:
            errors.append(
                "purchase_cost cannot be negative."
            )
    except ValueError as exc:
        errors.append(str(exc))

    try:
        parse_date(
            data.get("purchase_date"),
            "purchase_date",
        )
    except ValueError as exc:
        errors.append(str(exc))

    supplier = normalize(
        data.get("supplier")
    )

    if supplier:
        try:
            find_supplier(supplier)
        except ValueError as exc:
            errors.append(str(exc))

    return errors


def validate_vehicle_batch(batch, file):
    headers, rows = read_vehicle_excel(file)

    validate_headers(headers)

    batch.total_rows = len(rows)
    batch.valid_rows = 0
    batch.invalid_rows = 0

    batch.errors.all().delete()

    for row_number, data in rows:
        errors = validate_vehicle_row(
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
def import_vehicle_batch(batch, file):
    batch.status = batch.Status.IMPORTING
    batch.started_at = timezone.now()
    batch.save(
        update_fields=[
            "status",
            "started_at",
        ]
    )

    headers, rows = read_vehicle_excel(file)

    validate_headers(headers)

    imported = 0

    for row_number, data in rows:
        registration_number = normalize(
            data.get("registration_number")
        )

        if Vehicle.objects.filter(
            registration_number__iexact=
            registration_number
        ).exists():
            raise ValueError(
                f"Vehicle '{registration_number}' "
                "already exists."
            )

        vehicle = Vehicle.objects.create(
            registration_number=
                registration_number,

            make=normalize(
                data.get("make")
            ),

            model=normalize(
                data.get("model")
            ),

            year=parse_integer(
                data.get("year"),
                "year",
            ),

            color=normalize(
                data.get("color")
            ),

            vin=normalize(
                data.get("vin")
            ),

            engine_number=normalize(
                data.get("engine_number")
            ),

            vehicle_type=normalize(
                data.get("vehicle_type")
            ),

            fuel_type=normalize(
                data.get("fuel_type")
            ),

            status=normalize(
                data.get("status")
            ) or Vehicle._meta.get_field(
                "status"
            ).get_default(),

            purchase_date=parse_date(
                data.get("purchase_date"),
                "purchase_date",
            ),

            purchase_cost=parse_decimal(
                data.get("purchase_cost"),
                "purchase_cost",
            ),

            supplier=find_supplier(
                data.get("supplier")
            ),

            current_mileage=parse_integer(
                data.get("current_mileage"),
                "current_mileage",
            ) or 0,

            notes=normalize(
                data.get("notes")
            ),
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