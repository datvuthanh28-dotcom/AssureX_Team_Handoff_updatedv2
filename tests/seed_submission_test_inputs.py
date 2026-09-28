#!/usr/bin/env python3
from __future__ import annotations

import json
import secrets
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "assurex_web" / "backend"
sys.path.insert(0, str(BACKEND))

from app.auth_routes import hash_password, record_audit  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import CustomerAccount, Product, RegisteredProduct, Warranty  # noqa: E402
from sqlalchemy import select  # noqa: E402

PASSWORD = "TestPass123!"
TODAY = date.today()
STAMP = datetime.utcnow().strftime("%Y%m%d%H%M%S")

CASES = [
    {
        "case": "submit-valid",
        "email": f"submit.valid.{STAMP}@assurex.local",
        "full_name": "Submit Test Valid Customer",
        "product_name": "Submit Test Laptop Valid",
        "category": "Laptop",
        "model": "SUB-LAP-VALID",
        "warranty_months": 24,
        "purchase_days_ago": 75,
        "claim_inputs": {
            "Incident Date": (TODAY - timedelta(days=2)).isoformat(),
            "Fault Category": "Power Failure",
            "Fault Description": "Not required because category is predefined",
            "Previous Repair": "No",
            "Purchase proof?": "Yes",
            "Serial/product identity proof?": "Yes",
            "Fault evidence?": "Yes",
        },
        "expected": "Valid / WARRANTY candidate",
    },
    {
        "case": "submit-invalid",
        "email": f"submit.invalid.{STAMP}@assurex.local",
        "full_name": "Submit Test Invalid Customer",
        "product_name": "Submit Test Smartphone Invalid",
        "category": "Smartphone",
        "model": "SUB-PHN-INVALID",
        "warranty_months": 12,
        "purchase_days_ago": 60,
        "claim_inputs": {
            "Incident Date": (TODAY - timedelta(days=1)).isoformat(),
            "Fault Category": "Liquid Damage",
            "Fault Description": "Not required because category is predefined",
            "Previous Repair": "No",
            "Purchase proof?": "Yes",
            "Serial/product identity proof?": "Yes",
            "Fault evidence?": "Yes",
        },
        "expected": "Invalid / NOT_WARRANTY because Liquid Damage is excluded",
    },
    {
        "case": "submit-manual-review",
        "email": f"submit.manual.{STAMP}@assurex.local",
        "full_name": "Submit Test Manual Review Customer",
        "product_name": "Submit Test Laptop Manual Review",
        "category": "Laptop",
        "model": "SUB-LAP-MANUAL",
        "warranty_months": 24,
        "purchase_days_ago": 110,
        "claim_inputs": {
            "Incident Date": (TODAY - timedelta(days=5)).isoformat(),
            "Fault Category": "Battery Problem",
            "Fault Description": "Not required because category is predefined",
            "Previous Repair": "No",
            "Purchase proof?": "Yes",
            "Serial/product identity proof?": "No",
            "Fault evidence?": "No",
        },
        "expected": "Manual Review / REVIEW_REQUIRED because required evidence answers are missing",
    },
]


def add_months_approx(start: date, months: int) -> date:
    return start + timedelta(days=months * 30)


def ensure_customer(db, case):
    account = db.scalar(select(CustomerAccount).where(CustomerAccount.email == case["email"]))
    if account:
        return account
    salt = secrets.token_hex(16)
    account = CustomerAccount(
        email=case["email"],
        role="CUSTOMER",
        is_active=True,
        full_name=case["full_name"],
        password_salt=salt,
        password_hash=hash_password(PASSWORD, salt),
    )
    db.add(account)
    db.flush()
    record_audit(db, account=account, action="ACCOUNT_CREATED", resource_type="ACCOUNT", resource_id=str(account.id), details={"source": "submission_test_seed"})
    return account


def create_input_record(db, idx, case):
    account = ensure_customer(db, case)
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
        serial_number=f"SUBMIT-{idx:02d}-{STAMP[-6:]}",
        purchase_date=purchase.isoformat(),
        purchase_price=899 + idx * 100,
        retailer="AssureX Submission Test Store",
        is_active=True,
    )
    db.add(registered)
    db.flush()

    expiry = add_months_approx(purchase, case["warranty_months"])
    warranty = Warranty(
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
    )
    db.add(warranty)
    db.flush()

    return {
        "case": case["case"],
        "customer_email": account.email,
        "password": PASSWORD,
        "registration_code": f"REG-{registered.id:05d}",
        "product": product.name,
        "product_category": product.category,
        "expected": case["expected"],
        "claim_inputs": case["claim_inputs"],
    }


def main():
    rows = []
    with SessionLocal() as db:
        for idx, case in enumerate(CASES, 1):
            rows.append(create_input_record(db, idx, case))
        db.commit()

    out = ROOT / "docs" / "SUBMISSION_TEST_INPUT_RECORDS.md"
    lines = [
        "# Submission Test Input Records",
        "",
        f"Generated at: {datetime.utcnow().isoformat()}Z",
        "",
        f"Password for all customer accounts: `{PASSWORD}`",
        "",
        "Use these records in the Customer Portal to submit new claims yourself.",
        "",
        "| Case | Customer Login | Registration Code | Expected Result |",
        "|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| `{r['case']}` | `{r['customer_email']}` | `{r['registration_code']}` | {r['expected']} |")
    lines.append("")
    for r in rows:
        lines.extend([
            f"## {r['case']}",
            "",
            f"- Login: `{r['customer_email']}` / `{PASSWORD}`",
            f"- Registered Product Code: `{r['registration_code']}`",
            f"- Product: {r['product']} ({r['product_category']})",
            f"- Expected: {r['expected']}",
            "- Submit Claim inputs:",
        ])
        for key, value in r["claim_inputs"].items():
            lines.append(f"  - {key}: `{value}`")
        lines.append("")
    out.write_text("\n".join(lines) + "\n")
    print(json.dumps(rows, indent=2))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
