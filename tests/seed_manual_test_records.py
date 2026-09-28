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
from app.models import CustomerAccount, CustomerClaim, CustomerClaimDecision, Product, RegisteredProduct, Warranty, WarrantyTicket  # noqa: E402
from app.ml.model_service import predict_claim  # noqa: E402
from sqlalchemy import select  # noqa: E402

PASSWORD = "TestPass123!"
TODAY = date.today()

CASES = [
    {
        "slug": "valid",
        "name": "E2E Valid Manufacturing Defect",
        "email": "test.valid@assurex.local",
        "product_category": "Laptop",
        "product_name": "AssureX Test Laptop Valid",
        "model": "AX-LAP-VALID",
        "problem_category": "Power Failure",
        "description": "Power / Mainboard Failure",
        "purchase_days_ago": 90,
        "incident_days_ago": 2,
        "previous_repair": "No",
        "repair_centre": "",
        "repair_date": None,
        "evidence_answers": {
            "purchase_invoice_available": "Yes",
            "serial_image_available": "Yes",
            "fault_evidence_available": "Yes",
            "repair_report_available": "No",
        },
        "features": {
            "RepairAuthorized": "Not Applicable",
            "SerialNumberMatch": "Yes",
            "ProductModelConsistent": "Yes",
            "DuplicateClaimIndicator": "No",
            "ContradictionIndicator": "No",
            "OCRConfidence": 0.90,
            "ClaimReportingDelayDays": 2.0,
            "WarrantyRemainingDays": 640.0,
            "ClaimReportingWithinPeriod": "Yes",
            "FaultCovered": "Yes",
            "RequiredDocumentsComplete": "Yes",
            "MissingDocumentCount": 0.0,
            "ProductIdentityMatch": "Yes",
            "OCRQualityBand": "High",
        },
        "expected": "Valid path / reviewer approval candidate",
    },
    {
        "slug": "missing-evidence",
        "name": "E2E Missing Evidence Manual Review",
        "email": "test.missing.evidence@assurex.local",
        "product_category": "Laptop",
        "product_name": "AssureX Test Laptop Missing Evidence",
        "model": "AX-LAP-MISSING",
        "problem_category": "Battery Problem",
        "description": "Battery / Charging Problem",
        "purchase_days_ago": 120,
        "incident_days_ago": 4,
        "previous_repair": "No",
        "repair_centre": "",
        "repair_date": None,
        "evidence_answers": {
            "purchase_invoice_available": "Yes",
            "serial_image_available": "No",
            "fault_evidence_available": "No",
            "repair_report_available": "No",
        },
        "features": {
            "RepairAuthorized": "Not Applicable",
            "SerialNumberMatch": "Unknown",
            "ProductModelConsistent": "Unknown",
            "DuplicateClaimIndicator": "No",
            "ContradictionIndicator": "No",
            "OCRConfidence": 0.0,
            "ClaimReportingDelayDays": 4.0,
            "WarrantyRemainingDays": 610.0,
            "ClaimReportingWithinPeriod": "Yes",
            "FaultCovered": "Yes",
            "RequiredDocumentsComplete": "No",
            "MissingDocumentCount": 2.0,
            "ProductIdentityMatch": "Unknown",
            "OCRQualityBand": "Missing",
        },
        "expected": "Manual review due to missing serial/fault evidence",
    },
    {
        "slug": "liquid-damage",
        "name": "E2E Liquid Damage Exclusion",
        "email": "test.liquid.damage@assurex.local",
        "product_category": "Smartphone",
        "product_name": "AssureX Test Phone Liquid Damage",
        "model": "AX-PHN-LIQUID",
        "problem_category": "Liquid Damage",
        "description": "Liquid / Water Damage",
        "purchase_days_ago": 80,
        "incident_days_ago": 3,
        "previous_repair": "No",
        "repair_centre": "",
        "repair_date": None,
        "evidence_answers": {
            "purchase_invoice_available": "Yes",
            "serial_image_available": "Yes",
            "fault_evidence_available": "Yes",
            "repair_report_available": "No",
        },
        "features": {
            "RepairAuthorized": "Not Applicable",
            "SerialNumberMatch": "Yes",
            "ProductModelConsistent": "Yes",
            "DuplicateClaimIndicator": "No",
            "ContradictionIndicator": "No",
            "OCRConfidence": 0.90,
            "ClaimReportingDelayDays": 3.0,
            "WarrantyRemainingDays": 285.0,
            "ClaimReportingWithinPeriod": "Yes",
            "FaultCovered": "No",
            "RequiredDocumentsComplete": "Yes",
            "MissingDocumentCount": 0.0,
            "ProductIdentityMatch": "Yes",
            "OCRQualityBand": "High",
        },
        "expected": "Invalid / not covered because Liquid Damage is excluded",
    },
    {
        "slug": "unauthorized-repair",
        "name": "E2E Unauthorized Repair",
        "email": "test.unauthorized.repair@assurex.local",
        "product_category": "Laptop",
        "product_name": "AssureX Test Laptop Unauthorized Repair",
        "model": "AX-LAP-REPAIR",
        "problem_category": "Keyboard & Trackpad Failure",
        "description": "Keyboard / Trackpad Failure",
        "purchase_days_ago": 150,
        "incident_days_ago": 6,
        "previous_repair": "Yes",
        "repair_centre": "Local Third-Party Fix Shop",
        "repair_date": (TODAY - timedelta(days=30)).isoformat(),
        "evidence_answers": {
            "purchase_invoice_available": "Yes",
            "serial_image_available": "Yes",
            "fault_evidence_available": "Yes",
            "repair_report_available": "Yes",
        },
        "features": {
            "RepairAuthorized": "No",
            "SerialNumberMatch": "Yes",
            "ProductModelConsistent": "Yes",
            "DuplicateClaimIndicator": "No",
            "ContradictionIndicator": "No",
            "OCRConfidence": 0.90,
            "ClaimReportingDelayDays": 6.0,
            "WarrantyRemainingDays": 580.0,
            "ClaimReportingWithinPeriod": "Yes",
            "FaultCovered": "Yes",
            "RequiredDocumentsComplete": "Yes",
            "MissingDocumentCount": 0.0,
            "ProductIdentityMatch": "Yes",
            "OCRQualityBand": "High",
        },
        "expected": "Manual/invalid review trigger due to unauthorized repair",
    },
    {
        "slug": "other-category",
        "name": "E2E Other Category With Description",
        "email": "test.other.category@assurex.local",
        "product_category": "Monitor",
        "product_name": "AssureX Test Monitor Other Category",
        "model": "AX-MON-OTHER",
        "problem_category": "Other",
        "description": "Intermittent color calibration failure appears after the monitor warms up for 20 minutes.",
        "purchase_days_ago": 60,
        "incident_days_ago": 1,
        "previous_repair": "No",
        "repair_centre": "",
        "repair_date": None,
        "evidence_answers": {
            "purchase_invoice_available": "Yes",
            "serial_image_available": "Yes",
            "fault_evidence_available": "Yes",
            "repair_report_available": "No",
        },
        "features": {
            "RepairAuthorized": "Not Applicable",
            "SerialNumberMatch": "Yes",
            "ProductModelConsistent": "Yes",
            "DuplicateClaimIndicator": "No",
            "ContradictionIndicator": "No",
            "OCRConfidence": 0.90,
            "ClaimReportingDelayDays": 1.0,
            "WarrantyRemainingDays": 1035.0,
            "ClaimReportingWithinPeriod": "Yes",
            "FaultCovered": "Yes",
            "RequiredDocumentsComplete": "Yes",
            "MissingDocumentCount": 0.0,
            "ProductIdentityMatch": "Yes",
            "OCRQualityBand": "High",
        },
        "expected": "Other category validation path; description provided",
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
        username=None,
        role="CUSTOMER",
        is_active=True,
        full_name=case["name"],
        password_salt=salt,
        password_hash=hash_password(PASSWORD, salt),
    )
    db.add(account)
    db.flush()
    record_audit(db, account=account, action="ACCOUNT_CREATED", resource_type="ACCOUNT", resource_id=str(account.id), details={"source": "manual_test_seed"})
    return account


def create_case(db, idx: int, case: dict):
    account = ensure_customer(db, case)
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    product = Product(
        name=case["product_name"],
        category=case["product_category"],
        brand="AssureX",
        model=case["model"],
        warranty_months=36 if case["product_category"] == "Monitor" else 24 if case["product_category"] == "Laptop" else 12,
        is_active=True,
    )
    db.add(product)
    db.flush()

    purchase_date = TODAY - timedelta(days=case["purchase_days_ago"])
    serial = f"SEED-{idx:02d}-{case['slug'].upper()}-{stamp[-6:]}"
    registered = RegisteredProduct(
        account_id=account.id,
        product_id=product.id,
        serial_number=serial,
        purchase_date=purchase_date.isoformat(),
        purchase_price=799.0 + idx * 50,
        retailer="AssureX Manual Test Store",
        is_active=True,
    )
    db.add(registered)
    db.flush()

    expiry = add_months_approx(purchase_date, product.warranty_months)
    warranty = Warranty(
        registered_product_id=registered.id,
        start_date=purchase_date.isoformat(),
        end_date=expiry.isoformat(),
        status="Active" if expiry >= TODAY else "Expired",
        is_active=True,
        warranty_provider="AssureX Official Care",
        warranty_type="Standard",
        coverage_conditions="Covers manufacturer defects and normal-use component failures.",
        exclusions="Excludes liquid, impact, pest, power surge, unauthorized repair, and misuse damage.",
        service_center_details="AssureX Central Authorized Center",
    )
    db.add(warranty)
    db.flush()

    ticket_id = f"TCK-SEED{idx:02d}-{stamp[-6:]}"
    incident_date = TODAY - timedelta(days=case["incident_days_ago"])
    raw_input = {
        "product_code": f"REG-{registered.id:05d}",
        "incident_date": incident_date.isoformat(),
        "problem_category": case["problem_category"],
        "fault_description": "" if case["problem_category"] != "Other" else case["description"],
        "previous_repair": case["previous_repair"],
        "repair_centre": case["repair_centre"],
        "repair_date": case["repair_date"],
        **case["evidence_answers"],
        "customer_email": account.email,
        "submitted_at": datetime.utcnow().isoformat(),
        "seed_case": case["slug"],
    }
    features = case["features"]
    prediction = predict_claim(features)
    code_map = {"Valid Claim": "WARRANTY", "Invalid Claim": "NOT_WARRANTY", "Manual Review": "REVIEW_REQUIRED"}
    ai_prediction = code_map.get(prediction["predicted_class"], "REVIEW_REQUIRED")
    ticket_status = "REVIEW_REQUIRED" if ai_prediction == "REVIEW_REQUIRED" else "WAITING_REVIEW"

    ticket = WarrantyTicket(
        ticket_id=ticket_id,
        product_type=product.category,
        product_model=product.model,
        order_code=f"REG-{registered.id:05d}",
        purchase_date=registered.purchase_date,
        usage_duration=max(0, (TODAY - purchase_date).days // 30),
        problem_category=case["problem_category"],
        problem_description=case["description"],
        status=ticket_status,
        ai_prediction=ai_prediction,
        ai_confidence=float(prediction["confidence"]),
        model_features=features,
        customer_account_id=account.id,
        registered_product_id=registered.id,
        raw_input=raw_input,
        evidence={},
        model_name=prediction["model_name"],
        model_version=prediction["model_version"],
    )
    db.add(ticket)

    customer_claim = CustomerClaim(
        claim_id=ticket_id,
        customer_name=account.full_name,
        email=account.email,
        product_name=product.name,
        serial_number=registered.serial_number,
        purchase_date=registered.purchase_date,
        claim_amount=0.0,
        problem_category=case["problem_category"],
        fault_description=case["description"],
        status="Under Review",
        document_hashes={},
        previous_repair_date=case["repair_date"],
        repair_center_name=case["repair_centre"],
    )
    db.add(customer_claim)

    db.add(CustomerClaimDecision(
        claim_id=ticket_id,
        ml_prediction=prediction["predicted_class"],
        ml_confidence=float(prediction["confidence"]),
        probabilities=prediction.get("probabilities", {}),
        final_decision="Manual Review",
        requires_admin_review=1,
        decision_reasons=[case["expected"], "Seeded manual test record"],
        raw_input=raw_input,
        model_features=features,
        derived_data={"seed_case": case["slug"], "evidence_answers": case["evidence_answers"]},
        model_name=prediction["model_name"],
        python_model_name=prediction["model_name"],
        python_model_version=prediction["model_version"],
    ))

    record_audit(db, account=account, action="WARRANTY_TICKET_SUBMITTED", resource_type="CLAIM", resource_id=ticket_id, details={"source": "manual_test_seed", "case": case["slug"], "prediction": ai_prediction})
    return {
        "case": case["slug"],
        "customer_email": account.email,
        "password": PASSWORD,
        "registration_code": f"REG-{registered.id:05d}",
        "ticket_id": ticket_id,
        "product": product.name,
        "category": case["problem_category"],
        "expected": case["expected"],
        "ai_prediction": ai_prediction,
        "ml_prediction": prediction["predicted_class"],
        "confidence": round(float(prediction["confidence"]), 4),
    }


def main():
    rows = []
    with SessionLocal() as db:
        for idx, case in enumerate(CASES, 1):
            rows.append(create_case(db, idx, case))
        db.commit()

    out = ROOT / "docs" / "MANUAL_TEST_RECORDS.md"
    lines = [
        "# Manual Test Records",
        "",
        f"Generated at: {datetime.utcnow().isoformat()}Z",
        "",
        f"Password for all seeded customer accounts: `{PASSWORD}`",
        "",
        "| Case | Customer Login | Registration Code | Ticket ID | Category | AI/ML Result | What to test |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| `{r['case']}` | `{r['customer_email']}` | `{r['registration_code']}` | `{r['ticket_id']}` | {r['category']} | {r['ai_prediction']} / {r['ml_prediction']} ({r['confidence']}) | {r['expected']} |"
        )
    lines.extend([
        "",
        "Reviewer queue: log in as `reviewer` / `reviewer123` and open the warranty reviewer queue.",
        "Admin can also inspect these records in the claim/audit views.",
    ])
    out.write_text("\n".join(lines) + "\n")
    print(json.dumps(rows, indent=2))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
