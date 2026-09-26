import re
import unicodedata
from datetime import datetime


def strip_accents(value):
    value = str(value or "")
    value = (
        value
        .replace("Đ", "D")
        .replace("đ", "d")
    )

    return "".join(
        char
        for char in unicodedata.normalize(
            "NFD",
            value,
        )
        if unicodedata.category(char)
        != "Mn"
    )


def clean(value):
    if value is None:
        return None

    value = re.sub(
        r"\s+",
        " ",
        str(value),
    ).strip()

    value = value.strip(
        " \t\r\n:;|"
    )

    return value or None


def normalized(value):
    return strip_accents(
        value
    ).lower()


def is_label_line(
    line,
    patterns,
):
    normalized_line = (
        normalized(line)
        .strip(" :;|-")
    )

    return any(
        re.fullmatch(
            pattern,
            normalized_line,
            flags=re.IGNORECASE,
        )
        for pattern in patterns
    )


def value_after_label(
    lines,
    patterns,
):
    for index, line in enumerate(lines):
        if not is_label_line(
            line,
            patterns,
        ):
            continue

        if index + 1 < len(lines):
            return (
                lines[index + 1],
                index + 1,
            )

    return None, None


def normalize_code(value):
    value = clean(value)

    if not value:
        return None

    value = value.upper()

    value = re.sub(
        r"\s+",
        "",
        value,
    )

    value = re.sub(
        r"[^A-Z0-9._/\-]",
        "",
        value,
    )

    return value or None


def normalize_date(value):
    value = clean(value)

    if not value:
        return None

    match = re.search(
        r"\b("
        r"\d{1,2}[/-]"
        r"\d{1,2}[/-]"
        r"\d{4}"
        r")\b",
        value,
    )

    if not match:
        return None

    value = match.group(1)

    formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%m/%d/%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(
                value,
                fmt,
            ).strftime("%Y-%m-%d")

        except ValueError:
            continue

    return None


def parse_warranty_months(value):
    value = clean(value)

    if not value:
        return None

    normalized_value = normalized(
        value
    )

    match = re.search(
        r"\b(\d{1,3})\s*"
        r"(thang|months?|nam|years?)\b",
        normalized_value,
    )

    if not match:
        return None

    amount = int(
        match.group(1)
    )

    unit = match.group(2)

    if unit in {
        "nam",
        "year",
        "years",
    }:
        return amount * 12

    return amount


def extract_warranty_fields(text):
    text = text or ""

    lines = [
        clean(line)
        for line in text.splitlines()
        if clean(line)
    ]

    # -----------------------------------------
    # PRODUCT
    # -----------------------------------------

    product_name, _ = value_after_label(
        lines,
        [
            r"ten\s+san\s+pham",
            r"san\s+pham",
            r"product\s+name",
            r"product",
        ],
    )

    # -----------------------------------------
    # MODEL
    # -----------------------------------------

    model_number, _ = value_after_label(
        lines,
        [
            r"model(?:\s+number|\s+no\.?)?",
            r"ma\s+model",
            r"ma\s+san\s+pham",
        ],
    )

    # -----------------------------------------
    # SERIAL
    #
    # Tesseract read "Số serial"
    # as "S6 serial" in this test image.
    # -----------------------------------------

    serial_number, serial_index = (
        value_after_label(
            lines,
            [
                r"(?:so|s\d+)\s*serial",
                r"serial(?:\s+number|\s+no\.?)?",
                r"s\s*/\s*n",
                r"so\s+may",
            ],
        )
    )

    # -----------------------------------------
    # WARRANTY NUMBER
    # -----------------------------------------

    warranty_number, _ = value_after_label(
        lines,
        [
            r"ma\s+phieu\s+bao\s+hanh",
            r"so\s+phieu\s+bao\s+hanh",
            r"ma\s+bao\s+hanh",
            r"warranty\s+card\s+number",
            r"warranty\s+number",
        ],
    )

    # -----------------------------------------
    # CUSTOMER / CONTACT / DEALER
    # -----------------------------------------

    customer_name, _ = value_after_label(
        lines,
        [
            r"ho\s+va\s+ten\s+khach\s+hang",
            r"ten\s+khach\s+hang",
            r"customer\s+name",
        ],
    )

    phone_number, _ = value_after_label(
        lines,
        [
            r"so\s+dien\s+thoai",
            r"dien\s+thoai",
            r"phone(?:\s+number)?",
            r"telephone",
        ],
    )

    email, _ = value_after_label(
        lines,
        [
            r"email",
            r"e-mail",
        ],
    )

    dealer_name, _ = value_after_label(
        lines,
        [
            r"dai\s+ly\s+ban\s+hang",
            r"dai\s+ly",
            r"dealer",
            r"seller",
        ],
    )

    dealer_address, _ = value_after_label(
        lines,
        [
            r"dia\s+chi\s+dai\s+ly",
            r"dealer\s+address",
        ],
    )

    warranty_status, _ = value_after_label(
        lines,
        [
            r"tinh\s+trang\s+bao\s+hanh",
            r"warranty\s+status",
        ],
    )

    # -----------------------------------------
    # PURCHASE DATE
    #
    # First try explicit label.
    # OCR sometimes misses the label but
    # still reads the actual date.
    # -----------------------------------------

    purchase_date, purchase_index = (
        value_after_label(
            lines,
            [
                r"ngay\s+mua(?:\s+hang)?",
                r"purchase\s+date",
                r"date\s+of\s+purchase",
            ],
        )
    )

    if not normalize_date(
        purchase_date
    ):
        start_index = (
            serial_index + 1
            if serial_index is not None
            else 0
        )

        purchase_date = None
        purchase_index = None

        for index in range(
            start_index,
            len(lines),
        ):
            if normalize_date(
                lines[index]
            ):
                purchase_date = (
                    lines[index]
                )
                purchase_index = index
                break

    # -----------------------------------------
    # WARRANTY DURATION
    #
    # OCR may miss "Thời hạn bảo hành:"
    # while retaining "24 thang".
    # -----------------------------------------

    warranty_duration, _ = (
        value_after_label(
            lines,
            [
                r"thoi\s+han\s+bao\s+hanh",
                r"warranty\s+duration",
                r"warranty\s+period",
            ],
        )
    )

    if (
        parse_warranty_months(
            warranty_duration
        )
        is None
    ):
        start_index = (
            purchase_index + 1
            if purchase_index is not None
            else (
                serial_index + 1
                if serial_index is not None
                else 0
            )
        )

        warranty_duration = None

        for index in range(
            start_index,
            min(
                len(lines),
                start_index + 8,
            ),
        ):
            if (
                parse_warranty_months(
                    lines[index]
                )
                is not None
            ):
                warranty_duration = (
                    lines[index]
                )
                break

    return {
        "product_name":
            clean(product_name),

        "model_number":
            normalize_code(
                model_number
            ),

        "serial_number":
            normalize_code(
                serial_number
            ),

        "purchase_date":
            normalize_date(
                purchase_date
            ),

        "warranty_duration_months":
            parse_warranty_months(
                warranty_duration
            ),

        "warranty_number":
            normalize_code(
                warranty_number
            ),

        "customer_name":
            clean(customer_name),

        "phone_number":
            clean(phone_number),

        "email":
            clean(email),

        "dealer_name":
            clean(dealer_name),

        "dealer_address":
            clean(dealer_address),

        "warranty_status":
            clean(warranty_status),
    }
