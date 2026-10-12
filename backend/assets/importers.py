from datetime import datetime

from django.db import transaction
from django.template.backends import django
from django.db.models import Q
from openpyxl import load_workbook

from company.models import Employee, Location

from imports.models import ImportBatch, ImportError

from .models import Asset
from . import models



ASSET_IMPORT_HEADERS = [
    "asset_code",
    "name",
    "category",
    "description",
    "manufacturer",
    "model_number",
    "serial_number",
    "purchase_date",
    "purchase_cost",
    "warranty_start",
    "warranty_expiry",
    "condition",
    "status",
    "supplier",
    "location",
    "employee",
    "notes",
]


REQUIRED_HEADERS = [
    "asset_code",
    "name",
    "category",
]


def normalize(value):
    if value is None:
        return ""

    return str(value).strip()


def parse_date(value):
    if value in (None, ""):
        return None

    if isinstance(value, datetime):
        return value.date()

    if hasattr(value, "year") and hasattr(value, "month") and hasattr(value, "day"):
        return value

    value = str(value).strip()

    for date_format in (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
    ):
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue

    raise ValueError(
        "Invalid date. Use YYYY-MM-DD, DD/MM/YYYY, or MM/DD/YYYY."
    )


def parse_decimal(value):
    if value in (None, ""):
        return None

    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        raise ValueError("Invalid monetary value.")


def find_location(value):
    value = normalize(value)

    if not value:
        return None

    if value.isdigit():
        location = Location.objects.filter(pk=int(value)).first()
        if location:
            return location

    return Location.objects.filter(name__iexact=value).first()


def find_employee(value):
    value = normalize(value)

    if not value:
        return None

    if value.isdigit():
        employee = Employee.objects.filter(pk=int(value)).first()
        if employee:
            return employee

    return Employee.objects.filter(
    Q(first_name__iexact=value)
    | Q(last_name__iexact=value)
    ).first()


def validate_headers(headers):
    headers = [
        normalize(header).lower()
        for header in headers
        if normalize(header)
    ]

    missing = [
        header
        for header in REQUIRED_HEADERS
        if header not in headers
    ]

    unsupported = [
        header
        for header in headers
        if header not in ASSET_IMPORT_HEADERS
    ]

    return headers, missing, unsupported


def read_asset_excel(uploaded_file):
    workbook = load_workbook(
        uploaded_file,
        read_only=True,
        data_only=True,
    )

    worksheet = workbook.active

    rows = list(
        worksheet.iter_rows(values_only=True)
    )

    if not rows:
        raise ValueError("The Excel file is empty.")

    headers, missing, unsupported = validate_headers(
        rows[0]
    )

    if missing:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(missing)
        )

    if unsupported:
        raise ValueError(
            "Unsupported columns: "
            + ", ".join(unsupported)
        )

    header_indexes = {
        header: index
        for index, header in enumerate(headers)
    }

    data_rows = []

    for row_number, row in enumerate(rows[1:], start=2):
        if not any(
            normalize(value)
            for value in row
        ):
            continue

        data = {}

        for header in headers:
            index = header_indexes[header]

            data[header] = (
                row[index]
                if index < len(row)
                else None
            )

        data_rows.append(
            {
                "row_number": row_number,
                "data": data,
            }
        )

    workbook.close()

    return data_rows


def validate_asset_row(data, row_number):
    errors = []

    asset_code = normalize(
        data.get("asset_code")
    )

    name = normalize(
        data.get("name")
    )

    category = normalize(
        data.get("category")
    )

    if not asset_code:
        errors.append(
            {
                "column": "asset_code",
                "code": "REQUIRED",
                "message": "Asset code is required.",
            }
        )

    if not name:
        errors.append(
            {
                "column": "name",
                "code": "REQUIRED",
                "message": "Asset name is required.",
            }
        )

    if not category:
        errors.append(
            {
                "column": "category",
                "code": "REQUIRED",
                "message": "Asset category is required.",
            }
        )

    if asset_code:
        if Asset.objects.filter(
            asset_code=asset_code
        ).exists():
            errors.append(
                {
                    "column": "asset_code",
                    "code": "DUPLICATE",
                    "message": (
                        f"Asset code '{asset_code}' "
                        "already exists."
                    ),
                }
            )

    purchase_date = None
    warranty_start = None
    warranty_expiry = None

    try:
        purchase_date = parse_date(
            data.get("purchase_date")
        )
    except ValueError as exc:
        errors.append(
            {
                "column": "purchase_date",
                "code": "INVALID_DATE",
                "message": str(exc),
            }
        )

    try:
        warranty_start = parse_date(
            data.get("warranty_start")
        )
    except ValueError as exc:
        errors.append(
            {
                "column": "warranty_start",
                "code": "INVALID_DATE",
                "message": str(exc),
            }
        )

    try:
        warranty_expiry = parse_date(
            data.get("warranty_expiry")
        )
    except ValueError as exc:
        errors.append(
            {
                "column": "warranty_expiry",
                "code": "INVALID_DATE",
                "message": str(exc),
            }
        )

    if (
        purchase_date
        and warranty_start
        and warranty_start < purchase_date
    ):
        errors.append(
            {
                "column": "warranty_start",
                "code": "INVALID_DATE_RANGE",
                "message": (
                    "Warranty start cannot be earlier "
                    "than the purchase date."
                ),
            }
        )

    if (
        purchase_date
        and warranty_expiry
        and warranty_expiry < purchase_date
    ):
        errors.append(
            {
                "column": "warranty_expiry",
                "code": "INVALID_DATE_RANGE",
                "message": (
                    "Warranty expiry cannot be earlier "
                    "than the purchase date."
                ),
            }
        )

    try:
        purchase_cost = parse_decimal(
            data.get("purchase_cost")
        )

        if purchase_cost is not None and purchase_cost < 0:
            errors.append(
                {
                    "column": "purchase_cost",
                    "code": "NEGATIVE_VALUE",
                    "message": (
                        "Purchase cost cannot be negative."
                    ),
                }
            )

    except ValueError as exc:
        purchase_cost = None

        errors.append(
            {
                "column": "purchase_cost",
                "code": "INVALID_VALUE",
                "message": str(exc),
            }
        )

    location = find_location(
        data.get("location")
    )

    if normalize(data.get("location")) and not location:
        errors.append(
            {
                "column": "location",
                "code": "NOT_FOUND",
                "message": (
                    f"Location '{normalize(data.get('location'))}' "
                    "was not found."
                ),
            }
        )

    employee = find_employee(
        data.get("employee")
    )

    if normalize(data.get("employee")) and not employee:
        errors.append(
            {
                "column": "employee",
                "code": "NOT_FOUND",
                "message": (
                    f"Employee '{normalize(data.get('employee'))}' "
                    "was not found."
                ),
            }
        )

    if employee:
        employee_status = getattr(
            employee,
            "status",
            None,
        )

        if (
            employee_status is not None
            and str(employee_status).upper() != "ACTIVE"
        ):
            errors.append(
                {
                    "column": "employee",
                    "code": "INACTIVE_EMPLOYEE",
                    "message": (
                        "The selected employee is not active."
                    ),
                }
            )

    return errors


def validate_asset_batch(batch, uploaded_file):
    rows = read_asset_excel(
        uploaded_file
    )

    batch.total_rows = len(rows)
    batch.valid_rows = 0
    batch.invalid_rows = 0
    batch.status = ImportBatch.Status.VALIDATING
    batch.save(
        update_fields=[
            "total_rows",
            "valid_rows",
            "invalid_rows",
            "status",
        ]
    )

    ImportError.objects.filter(
        batch=batch
    ).delete()

    seen_asset_codes = set()

    for row in rows:
        row_number = row["row_number"]
        data = row["data"]

        errors = validate_asset_row(
            data,
            row_number,
        )

        asset_code = normalize(
            data.get("asset_code")
        )

        if asset_code:
            if asset_code in seen_asset_codes:
                errors.append(
                    {
                        "column": "asset_code",
                        "code": "DUPLICATE_IN_FILE",
                        "message": (
                            f"Asset code '{asset_code}' "
                            "appears more than once in this file."
                        ),
                    }
                )

            seen_asset_codes.add(
                asset_code
            )

        for error in errors:
            ImportError.objects.create(
                batch=batch,
                row_number=row_number,
                column_name=error["column"],
                error_code=error["code"],
                message=error["message"],
                row_data=data,
            )

        if errors:
            batch.invalid_rows += 1
        else:
            batch.valid_rows += 1

    if batch.invalid_rows:
        batch.status = ImportBatch.Status.FAILED
    else:
        batch.status = ImportBatch.Status.VALIDATED

    batch.save(
        update_fields=[
            "valid_rows",
            "invalid_rows",
            "status",
        ]
    )

    return batch


@transaction.atomic
def import_asset_batch(batch, uploaded_file):
    if batch.status != ImportBatch.Status.VALIDATED:
        raise ValueError(
            "Only a successfully validated import "
            "can be confirmed."
        )

    rows = read_asset_excel(
        uploaded_file
    )

    batch.status = ImportBatch.Status.IMPORTING
    batch.save(
        update_fields=["status"]
    )

    imported_count = 0

    for row in rows:
        data = row["data"]

        location = find_location(
            data.get("location")
        )

        employee = find_employee(
            data.get("employee")
        )

        purchase_date = parse_date(
            data.get("purchase_date")
        )

        warranty_start = parse_date(
            data.get("warranty_start")
        )

        warranty_expiry = parse_date(
            data.get("warranty_expiry")
        )

        purchase_cost = parse_decimal(
            data.get("purchase_cost")
        )

        asset = Asset.objects.create(
            asset_code=normalize(
                data.get("asset_code")
            ),
            name=normalize(
                data.get("name")
            ),
            category=normalize(
                data.get("category")
            ),
            description=normalize(
                data.get("description")
            ),
            manufacturer=normalize(
                data.get("manufacturer")
            ),
            model_number=normalize(
                data.get("model_number")
            ),
            serial_number=normalize(
                data.get("serial_number")
            ),
            purchase_date=purchase_date,
            purchase_cost=purchase_cost,
            warranty_start=warranty_start,
            warranty_expiry=warranty_expiry,
            condition=normalize(
                data.get("condition")
            ) or Asset.Condition.GOOD,
            status=normalize(
                data.get("status")
            ) or Asset.Status.AVAILABLE,
            supplier_id=(
                int(data["supplier"])
                if normalize(data.get("supplier")).isdigit()
                else None
            ),
            location=location,
            employee=employee,
            notes=normalize(
                data.get("notes")
            ),
        )

        # Create the initial asset history.
        from .models import AssetHistory

        AssetHistory.objects.create(
            asset=asset,
            event_type=AssetHistory.EventType.CREATED,
            performed_by=batch.uploaded_by,
            new_status=asset.status,
            new_condition=asset.condition,
            new_location=asset.location,
            new_employee=asset.employee,
            description=(
                f"Asset imported from Excel "
                f"batch #{batch.id}."
            ),
            snapshot={
                "asset_code": asset.asset_code,
                "name": asset.name,
                "status": asset.status,
                "condition": asset.condition,
                "location_id": (
                    asset.location_id
                    if asset.location_id
                    else None
                ),
                "employee_id": (
                    asset.employee_id
                    if asset.employee_id
                    else None
                ),
            },
        )

        imported_count += 1

    batch.imported_rows = imported_count
    batch.status = ImportBatch.Status.COMPLETED
    batch.completed_at = datetime.now()
    batch.save(
        update_fields=[
            "imported_rows",
            "status",
            "completed_at",
        ]
    )

    return batch