from datetime import datetime


CRITICAL_FIELDS = {
    "serial_number": "Serial Number",
    "model_number": "Model Number",
    "purchase_date": "Purchase Date",
    "warranty_duration_months":
        "Warranty Duration",
}


def _normalize_text(value):
    if value is None:
        return None

    return " ".join(
        str(value)
        .strip()
        .lower()
        .split()
    )


def _normalize_date(value):
    if value in (None, ""):
        return None

    value = str(value).strip()

    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%m/%d/%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(
                value,
                fmt,
            ).strftime("%Y-%m-%d")
        except ValueError:
            pass

    return _normalize_text(value)


def _normalize_months(value):
    if value in (None, ""):
        return None

    try:
        return int(float(value))
    except (TypeError, ValueError):
        return _normalize_text(value)


def _normalize(field, value):
    if field == "purchase_date":
        return _normalize_date(value)

    if field == "warranty_duration_months":
        return _normalize_months(value)

    return _normalize_text(value)


def compare_warranty_data(
    extracted_data,
    customer_data,
):
    extracted_data = extracted_data or {}
    customer_data = customer_data or {}

    comparisons = {}
    mismatches = []

    for field, label in CRITICAL_FIELDS.items():
        document_value = extracted_data.get(
            field
        )

        customer_value = customer_data.get(
            field
        )

        # OCR could not read this field.
        # Do not claim a mismatch.
        if document_value in (
            None,
            "",
        ):
            comparisons[field] = {
                "label": label,
                "document_value": None,
                "customer_value":
                    customer_value,
                "match": None,
                "status":
                    "not_extracted",
            }

            continue

        document_normalized = _normalize(
            field,
            document_value,
        )

        customer_normalized = _normalize(
            field,
            customer_value,
        )

        match = (
            document_normalized
            == customer_normalized
        )

        comparisons[field] = {
            "label": label,
            "document_value":
                document_value,
            "customer_value":
                customer_value,
            "match": match,
            "status":
                "match"
                if match
                else "mismatch",
        }

        if not match:
            mismatches.append(field)

    return {
        "has_mismatch":
            len(mismatches) > 0,
        "mismatch_fields":
            mismatches,
        "comparisons":
            comparisons,
    }
