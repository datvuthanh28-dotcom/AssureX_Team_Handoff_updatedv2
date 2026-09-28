#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "assurex_web" / "backend"
sys.path.insert(0, str(BACKEND))

from app.database import SessionLocal  # noqa: E402
from app.models import CustomerAccount, Product, RegisteredProduct, Warranty  # noqa: E402
from sqlalchemy import select  # noqa: E402

TODAY = date.today()
STAMP = datetime.utcnow().strftime("%Y%m%d%H%M%S")
ACCOUNT_EMAIL = "123@gmail.com"

CASES = [
    {
        "case": "VALID",
        "product_name": "123 Test Laptop Valid",
        "category": "Laptop",
        "model": "T123-VALID",
        "warranty_months": 24,
        "purchase_days_ago": 80,
        "inputs": {
            "Incident Date": (TODAY - timedelta(days=2)).isoformat(),
            "Fault Category": "Power Failure",
            "Fault Description": "Leave blank / not required",
            "Previous Repair": "No",
            "Purchase proof?": "Yes",
            "Serial/product identity proof?": "Yes",
            "Fault evidence?": "Yes",
        },
        "expected": "WARRANTY → Claim Status: Waiting to proceed",
    },
    {
        "case": "INVALID",
        "product_name": "123 Test Phone Invalid",
        "category": "Smartphone",
        "model": "T123-INVALID",
        "warranty_months": 12,
        "purchase_days_ago": 70,
        "inputs": {
            "Incident Date": (TODAY - timedelta(days=1)).isoformat(),
            "Fault Category": "Liquid Damage",
            "Fault Description": "Leave blank / not required",
            "Previous Repair": "No",
            "Purchase proof?": "Yes",
            "Serial/product identity proof?": "Yes",
            "Fault evidence?": "Yes",
        },
        "expected": "NOT_WARRANTY / Invalid Claim",
    },
    {
        "case": "MANUAL_REVIEW",
        "product_name": "123 Test Laptop Manual Review",
        "category": "Laptop",
        "model": "T123-MANUAL",
        "warranty_months": 24,
        "purchase_days_ago": 110,
        "inputs": {
            "Incident Date": (TODAY - timedelta(days=5)).isoformat(),
            "Fault Category": "Battery Problem",
            "Fault Description": "Leave blank / not required",
            "Previous Repair": "No",
            "Purchase proof?": "Yes",
            "Serial/product identity proof?": "No",
            "Fault evidence?": "No",
        },
        "expected": "REVIEW_REQUIRED / Manual Review",
    },
]


def add_months_approx(start: date, months: int) -> date:
    return start + timedelta(days=months * 30)


def main():
    rows = []
    with SessionLocal() as db:
        account = db.scalar(select(CustomerAccount).where(CustomerAccount.email == ACCOUNT_EMAIL))
        if account is None:
            raise SystemExit(f"Account {ACCOUNT_EMAIL} not found. Please register/login once first.")
        for index, case in enumerate(CASES, 1):
            product = Product(
                name=case["product_name"],
                category=case["category"],
                brand="AssureX",
                model=case["model"],
                warranty_months=case["warranty_months"],
                is_active=True,
            )
            db.add(product)
            db.flush()
            purchase = TODAY - timedelta(days=case["purchase_days_ago"])
            registered = RegisteredProduct(
                account_id=account.id,
                product_id=product.id,
                serial_number=f"123-{case['case']}-{STAMP[-6:]}",
                purchase_date=purchase.isoformat(),
                purchase_price=900 + index * 50,
                retailer="AssureX 123 Test Store",
                is_active=True,
            )
            db.add(registered)
            db.flush()
            expiry = add_months_approx(purchase, case["warranty_months"])
            db.add(Warranty(
                registered_product_id=registered.id,
                start_date=purchase.isoformat(),
                end_date=expiry.isoformat(),
                status="Active",
                is_active=True,
                warranty_provider="AssureX Official Care",
                warranty_type="Standard",
                coverage_conditions="Covers manufacturer defects and normal-use component failures.",
                exclusions="Excludes liquid, impact, pest, power surge, unauthorized repair, and misuse damage.",
                service_center_details="AssureX Central Authorized Center",
            ))
            rows.append({
                "case": case["case"],
                "login_email": ACCOUNT_EMAIL,
                "registration_code": f"REG-{registered.id:05d}",
                "product": case["product_name"],
                "product_category": case["category"],
                "expected": case["expected"],
                "inputs": case["inputs"],
            })
        db.commit()

    out = ROOT / "docs" / "SUBMIT_CLAIM_123_GMAIL_TEST_DATA.md"
    lines = [
        "# Submit Claim Test Data for 123@gmail.com",
        "",
        f"Generated at: {datetime.utcnow().isoformat()}Z",
        "",
        "Login with your existing customer account: `123@gmail.com`.",
        "",
        "| Case | Registered Product Code | Expected Result |",
        "|---|---|---|",
    ]
    for row in rows:
        lines.append(f"| `{row['case']}` | `{row['registration_code']}` | {row['expected']} |")
    lines.append("")
    for row in rows:
        lines.extend([
            f"## {row['case']}",
            "",
            f"- Registered Product Code: `{row['registration_code']}`",
            f"- Product: {row['product']} ({row['product_category']})",
            f"- Expected Result: {row['expected']}",
            "- Fill Submit Claim fields:",
        ])
        for key, value in row["inputs"].items():
            lines.append(f"  - {key}: `{value}`")
        lines.append("")
    out.write_text("\n".join(lines) + "\n")
    print(json.dumps(rows, indent=2))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
