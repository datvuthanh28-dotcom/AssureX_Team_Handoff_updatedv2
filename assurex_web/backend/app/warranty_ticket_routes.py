from datetime import date, datetime
import csv
import io
import re
from pathlib import Path
from typing import Any, Literal
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth_routes import record_audit, require_roles
from app.models import (
    CustomerAccount,
    CustomerClaim,
    CustomerClaimDecision,
    Product,
    RegisteredProduct,
    Warranty,
    WarrantyTicket,
)
from app.ml.model_service import MODEL_14_FEATURES, predict_claim
from app.ocr.ocr_service import extract_warranty_image

router = APIRouter(
    prefix="/api",
    tags=["Warranty Claim Management System"],
)

# Allowed Product Types according to SRS / Specification
ALLOWED_PRODUCT_TYPES = {
    "Air Conditioner",
    "Camera",
    "Laptop",
    "Printer",
    "Refrigerator",
    "Smartphone",
    "Television",
    "Washing Machine",
    "Tablet",
    "Monitor",
    "Other",
}

# ==============================================================================
# PYDANTIC SCHEMAS - 14 FINAL ML FEATURES
# ==============================================================================

class EvidenceReference(BaseModel):
    document_id: str
    filename: str
    file_url: str
    sha256: str | None = None
    content_type: str | None = None


class WarrantyClaimCreatePayload(BaseModel):
    """Customer-entered facts only; engineered ML fields are rejected by schema."""

    model_config = ConfigDict(extra="forbid")

    product_code: str = Field(min_length=1, max_length=30)
    incident_date: date
    fault_description: str = Field(min_length=10, max_length=5000)
    previous_repair: Literal["Yes", "No"]
    repair_centre: str | None = Field(default=None, max_length=150)
    repair_date: date | None = None
    evidence: dict[str, EvidenceReference] = Field(default_factory=dict)

    @field_validator("repair_date", mode="before")
    @classmethod
    def blank_repair_date_as_none(cls, value):
        if value == "":
            return None
        return value


class ModelPredictRequest(BaseModel):
    ticket_id: str | None = None
    RepairAuthorized: str = "Not Applicable"
    SerialNumberMatch: str = "Yes"
    ProductModelConsistent: str = "Yes"
    DuplicateClaimIndicator: str = "No"
    ContradictionIndicator: str = "No"
    OCRConfidence: float = 0.90
    ClaimReportingDelayDays: float = 5.0
    WarrantyRemainingDays: float = 180.0
    ClaimReportingWithinPeriod: str = "Yes"
    FaultCovered: str = "Yes"
    RequiredDocumentsComplete: str = "Yes"
    MissingDocumentCount: float = 0.0
    ProductIdentityMatch: str = "Yes"
    OCRQualityBand: str = "High"


class ModelPredictResponse(BaseModel):
    prediction: Literal["WARRANTY", "NOT_WARRANTY", "REVIEW_REQUIRED"]
    confidence: float
    predicted_class: str
    probabilities: dict[str, float]
    model_name: str
    model_version: str


class ReviewerDecisionPayload(BaseModel):
    decision: Literal["APPROVE", "REJECT"]
    reviewer_note: str | None = None


# ==============================================================================
# AI MODEL PREDICTION ENGINE (14 FINAL FEATURES)
# ==============================================================================

def execute_ai_prediction_14(features_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Evaluates claim using the 14 finalized features using the trained ML model.
    Maps:
      - 'Valid Claim'    -> 'WARRANTY' (confidence)
      - 'Invalid Claim'  -> 'NOT_WARRANTY' (confidence)
      - 'Manual Review'  -> 'REVIEW_REQUIRED' (confidence)
    """
    prediction_result = predict_claim(features_dict)
    raw_class = prediction_result.get("predicted_class", "Manual Review")
    conf = float(prediction_result.get("confidence", 0.85))

    if raw_class == "Valid Claim":
        code = "WARRANTY"
    elif raw_class == "Invalid Claim":
        code = "NOT_WARRANTY"
    else:
        code = "REVIEW_REQUIRED"

    return {
        "prediction": code,
        "confidence": round(conf, 4),
        "predicted_class": raw_class,
        "probabilities": prediction_result.get("probabilities", {}),
        "model_name": prediction_result.get("model_name", "Gradient Boosting (14 Features)"),
        "model_version": prediction_result.get("model_version", "v3-final-14feat"),
    }


def extract_14_features(data: WarrantyClaimCreatePayload | dict) -> dict[str, Any]:
    """Extract and validate clean 14 features from payload."""
    if isinstance(data, WarrantyClaimCreatePayload):
        raw = data.model_dump()
    else:
        raw = dict(data)

    # Defaults and type conversions for the 14 features
    try:
        ocr_conf = float(raw.get("OCRConfidence", 0.90))
    except (ValueError, TypeError):
        ocr_conf = 0.90
    ocr_conf = max(0.0, min(1.0, ocr_conf))

    try:
        delay = float(raw.get("ClaimReportingDelayDays", 0.0))
    except (ValueError, TypeError):
        delay = 0.0

    try:
        remaining_days = float(raw.get("WarrantyRemainingDays", 0.0))
    except (ValueError, TypeError):
        remaining_days = 0.0

    try:
        missing_count = float(raw.get("MissingDocumentCount", 0.0))
    except (ValueError, TypeError):
        missing_count = 0.0

    # Auto sync Quality Band if not explicitly provided
    quality_band = str(raw.get("OCRQualityBand", "")).strip()
    if not quality_band:
        if ocr_conf >= 0.85:
            quality_band = "High"
        elif ocr_conf >= 0.65:
            quality_band = "Medium"
        else:
            quality_band = "Low"

    # Auto sync Reporting Within Period if not explicitly set
    rep_period = str(raw.get("ClaimReportingWithinPeriod", "")).strip()
    if not rep_period:
        rep_period = "Yes" if delay <= 30 else "No"

    return {
        "RepairAuthorized": str(raw.get("RepairAuthorized") or "Not Applicable").strip(),
        "SerialNumberMatch": str(raw.get("SerialNumberMatch") or "Yes").strip(),
        "ProductModelConsistent": str(raw.get("ProductModelConsistent") or "Yes").strip(),
        "DuplicateClaimIndicator": str(raw.get("DuplicateClaimIndicator") or "No").strip(),
        "ContradictionIndicator": str(raw.get("ContradictionIndicator") or "No").strip(),
        "OCRConfidence": ocr_conf,
        "ClaimReportingDelayDays": delay,
        "WarrantyRemainingDays": remaining_days,
        "ClaimReportingWithinPeriod": rep_period,
        "FaultCovered": str(raw.get("FaultCovered") or "Yes").strip(),
        "RequiredDocumentsComplete": str(raw.get("RequiredDocumentsComplete") or "Yes").strip(),
        "MissingDocumentCount": missing_count,
        "ProductIdentityMatch": str(raw.get("ProductIdentityMatch") or "Yes").strip(),
        "OCRQualityBand": quality_band,
    }


# ==============================================================================
# API ENDPOINTS
# ==============================================================================

EVIDENCE_DIR = Path("app/uploads/evidence")
EXCLUDED_FAULT_TERMS = {
    "water", "liquid", "dropped", "falling", "shattered", "physical impact",
    "spilled", "tampered", "cracked glass", "misuse", "accident",
    "roi", "rơi", "vo", "vỡ", "be", "bể", "be man hinh", "bể màn hình",
    "roi vo", "rơi vỡ", "va dap", "va đập", "rot nuoc", "rớt nước",
    "vao nuoc", "vào nước", "ngam nuoc", "ngấm nước", "do nuoc", "đổ nước",
    "tray xuoc", "trầy xước", "nut", "nứt", "tamper", "tu sua", "tự sửa",
}
AUTHORIZED_REPAIR_TERMS = {
    "assurex", "official", "authorized", "authorised", "premier",
    "apple", "dell", "hp", "lenovo", "samsung",
}


def _registration_id(product_code: str) -> int:
    match = re.fullmatch(r"REG-(\d+)", product_code.strip().upper())
    if not match:
        raise HTTPException(
            status_code=422,
            detail="Registered Product Code must use the registration code shown in My Products (REG-xxxxx).",
        )
    return int(match.group(1))


def _owned_product(db: Session, account: CustomerAccount, product_code: str):
    registration_id = _registration_id(product_code)
    row = db.execute(
        select(RegisteredProduct, Product, Warranty)
        .join(Product, Product.id == RegisteredProduct.product_id)
        .outerjoin(Warranty, Warranty.registered_product_id == RegisteredProduct.id)
        .where(
            RegisteredProduct.id == registration_id,
            RegisteredProduct.account_id == account.id,
            RegisteredProduct.is_active.is_(True),
        )
    ).first()
    if row is None:
        # Do not reveal whether the code belongs to a different customer.
        raise HTTPException(status_code=404, detail="Registered product not found.")
    return row


def _serialize_owned_product(registered, product, warranty):
    expiry = warranty.end_date if warranty else None
    return {
        "registered_product_id": registered.id,
        "product_code": f"REG-{registered.id:05d}",
        "product_name": product.name,
        "category": product.category,
        "brand": product.brand,
        "model_number": product.model,
        "serial_number": registered.serial_number,
        "purchase_date": registered.purchase_date,
        "purchase_price": registered.purchase_price,
        "retailer": registered.retailer,
        "warranty_months": product.warranty_months,
        "warranty_start_date": warranty.start_date if warranty else registered.purchase_date,
        "warranty_expiry_date": expiry,
        "warranty_provider": warranty.warranty_provider if warranty else "AssureX Official Care",
        "status": (
            "expired"
            if expiry and date.fromisoformat(expiry) < date.today()
            else "active"
        ),
    }


def _ocr_evidence(evidence: dict[str, EvidenceReference]):
    candidates = []
    extracted = {}
    for key in ("serial_image", "purchase_invoice"):
        reference = evidence.get(key)
        if not reference or not reference.document_id.startswith("EVD-"):
            continue
        matches = list(EVIDENCE_DIR.glob(f"{reference.document_id}.*"))
        if not matches or matches[0].suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            continue
        try:
            result = extract_warranty_image(matches[0])
        except Exception:
            continue
        candidates.append(float(result.get("ocr_confidence") or 0))
        for field, value in (result.get("extracted_data") or {}).items():
            if value and not extracted.get(field):
                extracted[field] = value
    return (max(candidates) if candidates else 0.0), extracted


def _derive_features(db, account, registered, product, warranty, payload):
    today = date.today()
    evidence = payload.evidence
    ocr_confidence, ocr_data = _ocr_evidence(evidence)
    ocr_serial = str(ocr_data.get("serial_number") or "").strip().casefold()
    ocr_model = str(ocr_data.get("model_number") or "").strip().casefold()
    expected_serial = registered.serial_number.strip().casefold()
    expected_model = product.model.strip().casefold()

    serial_match = "Unknown" if not ocr_serial else ("Yes" if ocr_serial == expected_serial else "No")
    model_match = "Unknown" if not ocr_model else ("Yes" if ocr_model == expected_model else "No")
    product_identity = (
        "Yes" if serial_match == "Yes" and model_match in {"Yes", "Unknown"}
        else "No" if "No" in {serial_match, model_match}
        else "Unknown"
    )

    duplicate = db.scalar(
        select(func.count()).select_from(WarrantyTicket).where(
            WarrantyTicket.registered_product_id == registered.id,
            WarrantyTicket.status.in_(("PENDING_AI", "WAITING_REVIEW", "REVIEW_REQUIRED")),
        )
    ) or 0
    delay = max(0, (today - payload.incident_date).days)
    expiry = date.fromisoformat(warranty.end_date) if warranty else None
    remaining = (expiry - today).days if expiry else 0
    description = payload.fault_description.casefold()
    fault_covered = "No" if any(term in description for term in EXCLUDED_FAULT_TERMS) else "Yes"

    # A claim can be submitted without uploads. Missing optional evidence is
    # retained as a model signal and can route the ticket to manual review.
    missing_count = sum(
        1 for name in ("purchase_invoice", "serial_image", "fault_evidence")
        if name not in evidence
    )
    if payload.previous_repair == "Yes" and "repair_report" not in evidence:
        missing_count += 1

    recorded_repair = db.scalar(
        select(func.count()).select_from(WarrantyTicket).where(
            WarrantyTicket.registered_product_id == registered.id,
            WarrantyTicket.raw_input["previous_repair"].as_string() == "Yes",
        )
    ) or 0
    has_repair_history = payload.previous_repair == "Yes" or bool(recorded_repair)

    if not has_repair_history:
        repair_authorized = "Not Applicable"
    elif "repair_report" not in evidence:
        repair_authorized = "Unknown"
    else:
        centre = (payload.repair_centre or "").casefold()
        repair_authorized = "Yes" if any(term in centre for term in AUTHORIZED_REPAIR_TERMS) else "No"

    contradiction = any((
        payload.incident_date < date.fromisoformat(registered.purchase_date),
        payload.incident_date > today,
        bool(payload.repair_date and payload.repair_date > today),
        bool(payload.repair_date and payload.repair_date < date.fromisoformat(registered.purchase_date)),
    ))
    quality = "High" if ocr_confidence >= .85 else "Medium" if ocr_confidence >= .65 else "Low" if ocr_confidence > 0 else "Missing"

    return {
        "RepairAuthorized": repair_authorized,
        "SerialNumberMatch": serial_match,
        "ProductModelConsistent": model_match,
        "DuplicateClaimIndicator": "Yes" if duplicate else "No",
        "ContradictionIndicator": "Yes" if contradiction else "No",
        "OCRConfidence": round(ocr_confidence, 4),
        "ClaimReportingDelayDays": float(delay),
        "WarrantyRemainingDays": float(remaining),
        "ClaimReportingWithinPeriod": "Yes" if delay <= 30 else "No",
        "FaultCovered": fault_covered,
        "RequiredDocumentsComplete": "Yes" if missing_count == 0 else "No",
        "MissingDocumentCount": float(missing_count),
        "ProductIdentityMatch": product_identity,
        "OCRQualityBand": quality,
    }, ocr_data


@router.get("/claims/v3/product/{product_code}")
def lookup_claim_product(
    product_code: str,
    account: CustomerAccount = Depends(require_roles("CUSTOMER")),
    db: Session = Depends(get_db),
):
    registered, product, warranty = _owned_product(db, account, product_code)
    return _serialize_owned_product(registered, product, warranty)

@router.post(
    "/claims/v3/ticket",
    status_code=status.HTTP_201_CREATED,
    summary="Customer: submit raw claim facts; backend derives Model V3 features",
)
def create_warranty_claim(
    payload: WarrantyClaimCreatePayload,
    account: CustomerAccount = Depends(require_roles("CUSTOMER")),
    db: Session = Depends(get_db),
):
    if payload.previous_repair == "Yes" and not (payload.repair_centre or "").strip():
        raise HTTPException(status_code=422, detail="Repair centre is required for a previously repaired product.")

    registered, product, warranty = _owned_product(db, account, payload.product_code)
    features_14, ocr_data = _derive_features(
        db, account, registered, product, warranty, payload
    )
    ticket_id = f"TCK-{uuid.uuid4().hex[:8].upper()}"
    raw_input = payload.model_dump(mode="json", exclude={"evidence"})
    raw_input["customer_email"] = account.email
    raw_input["submitted_at"] = datetime.utcnow().isoformat()
    ticket = WarrantyTicket(
        ticket_id=ticket_id,
        product_type=product.category if product.category in ALLOWED_PRODUCT_TYPES else "Other",
        product_model=product.model,
        order_code=f"REG-{registered.id:05d}",
        purchase_date=registered.purchase_date,
        usage_duration=max(0, (date.today() - date.fromisoformat(registered.purchase_date)).days // 30),
        problem_category="Warranty Claim",
        problem_description=payload.fault_description,
        status="PENDING_AI",
        customer_account_id=account.id,
        registered_product_id=registered.id,
        raw_input=raw_input,
        evidence={key: value.model_dump() for key, value in payload.evidence.items()},
        model_features=features_14,
    )
    db.add(ticket)
    try:
        ai_res = execute_ai_prediction_14(features_14)
        ticket.ai_prediction = ai_res["prediction"]
        ticket.ai_confidence = ai_res["confidence"]
        ticket.model_name = ai_res["model_name"]
        ticket.model_version = ai_res["model_version"]
        ticket.status = "WAITING_REVIEW" if ai_res["prediction"] != "REVIEW_REQUIRED" else "REVIEW_REQUIRED"
        ticket.ai_error_message = None
    except Exception as exc:
        ticket.status = "AI_ERROR"
        ticket.ai_error_message = f"AI Prediction Failed: {str(exc)}"
    customer_claim = CustomerClaim(
        claim_id=ticket_id,
        customer_name=account.full_name or account.email,
        email=account.email,
        product_name=product.name,
        serial_number=registered.serial_number,
        purchase_date=registered.purchase_date,
        claim_amount=0.0,
        fault_description=payload.fault_description,
        status="Under Review" if ticket.status != "AI_ERROR" else "Manual Review",
        receipt_url=(ticket.evidence.get("purchase_invoice") or {}).get("file_url"),
        evidence_photo_url=(ticket.evidence.get("fault_evidence") or {}).get("file_url"),
        product_image_url=(ticket.evidence.get("serial_image") or {}).get("file_url"),
        repair_report_url=(ticket.evidence.get("repair_report") or {}).get("file_url"),
        document_hashes={key: value.get("sha256") for key, value in ticket.evidence.items()},
        previous_repair_date=payload.repair_date.isoformat() if payload.repair_date else None,
        repair_center_name=payload.repair_centre,
    )
    db.add(customer_claim)
    if ticket.ai_prediction:
        label_map = {
            "WARRANTY": "Valid Claim",
            "NOT_WARRANTY": "Invalid Claim",
            "REVIEW_REQUIRED": "Manual Review",
        }
        predicted_class = label_map.get(ticket.ai_prediction, "Manual Review")
        db.add(CustomerClaimDecision(
            claim_id=ticket_id,
            ml_prediction=predicted_class,
            ml_confidence=ticket.ai_confidence or 0.0,
            probabilities={},
            final_decision="Manual Review",
            requires_admin_review=1,
            decision_reasons=["Reviewer confirmation required"],
            raw_input=raw_input,
            model_features=features_14,
            derived_data={"ocr_extracted_data": ocr_data, "evidence": ticket.evidence},
            model_name=ticket.model_name or "Gradient Boosting V3",
            python_model_name=ticket.model_name,
            python_model_version=ticket.model_version,
        ))
    record_audit(
        db,
        account=account,
        action="WARRANTY_TICKET_SUBMITTED",
        resource_type="CLAIM",
        resource_id=ticket_id,
        details={
            "registered_product_id": registered.id,
            "model_version": ticket.model_version,
            "prediction": ticket.ai_prediction,
            "derived_feature_count": len(features_14),
        },
    )
    db.commit()
    db.refresh(ticket)
    owned_product = _serialize_owned_product(registered, product, warranty)
    return {
        "success": True,
        "message": "Claim stored and evaluated from backend-derived features.",
        "ticket": {
            **owned_product,
            "ticket_id": ticket.ticket_id,
            "status": ticket.status,
            "warranty_status": owned_product["status"],
            "customer_name": account.full_name or account.email,
            "customer_email": account.email,
            "fault_description": payload.fault_description,
            "evidence": ticket.evidence,
            "model_features": features_14,
            "ai_prediction": ticket.ai_prediction,
            "ai_confidence": ticket.ai_confidence,
            "ai_reason": "Backend-derived Model V3 assessment",
            "model_name": ticket.model_name,
            "model_version": ticket.model_version,
            "ocr_extracted_data": ocr_data,
            "ai_error_message": ticket.ai_error_message,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        },
    }


@router.post(
    "/model/predict",
    response_model=ModelPredictResponse,
    summary="Direct AI Model Prediction with 14 Features",
)
def predict_model_endpoint(request: ModelPredictRequest):
    """
    Direct endpoint for predicting a claim using the 14 features.
    """
    features_dict = request.model_dump()
    features_14 = extract_14_features(features_dict)
    res = execute_ai_prediction_14(features_14)

    return ModelPredictResponse(
        prediction=res["prediction"],
        confidence=res["confidence"],
        predicted_class=res["predicted_class"],
        probabilities=res["probabilities"],
        model_name=res["model_name"],
        model_version=res["model_version"],
    )


@router.get(
    "/warranty/claims",
    summary="List Warranty Claims (Alias for Reviewer and Portal)",
)
@router.get(
    "/warranty/reviewer/tickets",
    summary="Reviewer: List Tickets (Queue)",
)
def list_reviewer_tickets(
    status_filter: str = Query("ALL", description="ALL, WAITING_REVIEW, REVIEWED, PENDING_AI, AI_ERROR"),
    search: str | None = Query(None, description="Search by Ticket ID, Model, or Serial"),
    _: CustomerAccount = Depends(require_roles("ADMIN", "REVIEWER")),
    db: Session = Depends(get_db),
):
    """
    Returns list of tickets for Reviewer desk.
    """
    stmt = select(WarrantyTicket)

    if status_filter != "ALL":
        if status_filter == "WAITING_REVIEW":
            stmt = stmt.where(WarrantyTicket.status.in_(["WAITING_REVIEW", "REVIEW_REQUIRED"]))
        else:
            stmt = stmt.where(WarrantyTicket.status == status_filter)

    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                WarrantyTicket.ticket_id.ilike(pattern),
                WarrantyTicket.product_model.ilike(pattern),
                WarrantyTicket.order_code.ilike(pattern),
                WarrantyTicket.problem_description.ilike(pattern),
            )
        )

    stmt = stmt.order_by(WarrantyTicket.created_at.desc())
    tickets = db.scalars(stmt).all()

    items = []
    for t in tickets:
        items.append({
            "ticket_id": t.ticket_id,
            "product_type": t.product_type,
            "product_model": t.product_model,
            "order_code": t.order_code,
            "purchase_date": t.purchase_date,
            "usage_duration": t.usage_duration,
            "problem_category": t.problem_category,
            "problem_description": t.problem_description,
            "fault_description": t.problem_description,
            "customer_name": (t.raw_input or {}).get("customer_email", "Customer"),
            "customer_email": (t.raw_input or {}).get("customer_email", ""),
            "product_name": t.product_model,
            "product_code": t.order_code,
            "status": t.status,
            "raw_input": t.raw_input or {},
            "evidence": t.evidence or {},
            "model_features": t.model_features or {},
            "ai_prediction": t.ai_prediction,
            "ai_confidence": t.ai_confidence,
            "ai_error_message": t.ai_error_message,
            "reviewer_decision": t.reviewer_decision,
            "ground_truth": t.ground_truth,
            "reviewer_note": t.reviewer_note,
            "reviewed_at": t.reviewed_at.isoformat() if t.reviewed_at else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        })

    return {
        "total": len(items),
        "tickets": items,
    }


@router.get(
    "/warranty/reviewer/tickets/{ticket_id}",
    summary="Reviewer: Get Detailed Ticket",
)
def get_ticket_detail(
    ticket_id: str,
    _: CustomerAccount = Depends(require_roles("ADMIN", "REVIEWER")),
    db: Session = Depends(get_db),
):
    ticket = db.get(WarrantyTicket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Warranty ticket not found.")

    return {
        "ticket": {
            "ticket_id": ticket.ticket_id,
            "product_type": ticket.product_type,
            "product_model": ticket.product_model,
            "order_code": ticket.order_code,
            "purchase_date": ticket.purchase_date,
            "usage_duration": ticket.usage_duration,
            "problem_category": ticket.problem_category,
            "problem_description": ticket.problem_description,
            "fault_description": ticket.problem_description,
            "customer_name": (ticket.raw_input or {}).get("customer_email", "Customer"),
            "customer_email": (ticket.raw_input or {}).get("customer_email", ""),
            "status": ticket.status,
            "raw_input": ticket.raw_input or {},
            "evidence": ticket.evidence or {},
            "model_features": ticket.model_features or {},
            "ai_prediction": ticket.ai_prediction,
            "ai_confidence": ticket.ai_confidence,
            "ai_error_message": ticket.ai_error_message,
            "reviewer_decision": ticket.reviewer_decision,
            "ground_truth": ticket.ground_truth,
            "reviewer_note": ticket.reviewer_note,
            "reviewed_at": ticket.reviewed_at.isoformat() if ticket.reviewed_at else None,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
            "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
        }
    }


@router.post(
    "/reviewer/{ticket_id}/decision",
    summary="Reviewer: Submit Final Decision (Short Alias)",
)
@router.post(
    "/warranty/reviewer/tickets/{ticket_id}/decision",
    summary="Reviewer: Submit Final Decision (Becomes Ground Truth)",
)
def submit_reviewer_decision(
    ticket_id: str,
    payload: ReviewerDecisionPayload,
    account: CustomerAccount = Depends(require_roles("ADMIN", "REVIEWER")),
    db: Session = Depends(get_db),
):
    ticket = db.get(WarrantyTicket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Warranty ticket not found.")

    decision_choice = payload.decision
    if decision_choice not in {"APPROVE", "REJECT"}:
        raise HTTPException(status_code=400, detail="Decision must be APPROVE or REJECT.")

    # Ground truth mapping: APPROVE -> 'Valid Claim', REJECT -> 'Invalid Claim'
    ground_truth = "Valid Claim" if decision_choice == "APPROVE" else "Invalid Claim"

    ticket.reviewer_decision = decision_choice
    ticket.ground_truth = ground_truth
    ticket.reviewer_note = payload.reviewer_note.strip() if payload.reviewer_note else None
    ticket.status = "REVIEWED"
    ticket.reviewed_at = datetime.utcnow()

    customer_claim = db.scalar(
        select(CustomerClaim).where(CustomerClaim.claim_id == ticket_id)
    )
    if customer_claim is not None:
        customer_claim.status = "Approved" if decision_choice == "APPROVE" else "Rejected"
    customer_decision = db.scalar(
        select(CustomerClaimDecision).where(CustomerClaimDecision.claim_id == ticket_id)
    )
    if customer_decision is not None:
        customer_decision.reviewer_decision = customer_claim.status
        customer_decision.reviewer_comment = ticket.reviewer_note
        customer_decision.reviewed_at = ticket.reviewed_at

    record_audit(
        db,
        account=account,
        action="WARRANTY_TICKET_REVIEWED",
        resource_type="CLAIM",
        resource_id=ticket_id,
        details={"decision": decision_choice, "ground_truth": ground_truth},
    )

    db.commit()
    db.refresh(ticket)

    return {
        "success": True,
        "message": f"Ticket {ticket.ticket_id} marked as {decision_choice}. Ground truth set to '{ground_truth}'.",
        "ticket": {
            "ticket_id": ticket.ticket_id,
            "status": ticket.status,
            "reviewer_decision": ticket.reviewer_decision,
            "ground_truth": ticket.ground_truth,
            "reviewer_note": ticket.reviewer_note,
            "reviewed_at": ticket.reviewed_at.isoformat() if ticket.reviewed_at else None,
        },
    }


@router.get(
    "/warranty/reviewer/export/retraining-dataset",
    summary="Reviewer: Export Retraining Dataset (14 Features + Ground Truth)",
)
def export_retraining_dataset(
    format: str = Query("csv", description="Format: csv or json"),
    _: CustomerAccount = Depends(require_roles("ADMIN", "REVIEWER")),
    db: Session = Depends(get_db),
):
    """
    Exports reviewed claims dataset for ML retraining.
    Contains the 14 features plus 'ClaimClass' ground truth.
    """
    stmt = (
        select(WarrantyTicket)
        .where(WarrantyTicket.ground_truth.is_not(None))
        .order_by(WarrantyTicket.reviewed_at.desc())
    )
    tickets = db.scalars(stmt).all()

    records = []
    for t in tickets:
        feats = t.model_features or {}
        row = {
            "ClaimID": t.ticket_id,
            "RepairAuthorized": feats.get("RepairAuthorized", "Not Applicable"),
            "SerialNumberMatch": feats.get("SerialNumberMatch", "Yes"),
            "ProductModelConsistent": feats.get("ProductModelConsistent", "Yes"),
            "DuplicateClaimIndicator": feats.get("DuplicateClaimIndicator", "No"),
            "ContradictionIndicator": feats.get("ContradictionIndicator", "No"),
            "OCRConfidence": feats.get("OCRConfidence", 0.90),
            "ClaimReportingDelayDays": feats.get("ClaimReportingDelayDays", 0.0),
            "WarrantyRemainingDays": feats.get("WarrantyRemainingDays", 180.0),
            "ClaimReportingWithinPeriod": feats.get("ClaimReportingWithinPeriod", "Yes"),
            "FaultCovered": feats.get("FaultCovered", "Yes"),
            "RequiredDocumentsComplete": feats.get("RequiredDocumentsComplete", "Yes"),
            "MissingDocumentCount": feats.get("MissingDocumentCount", 0.0),
            "ProductIdentityMatch": feats.get("ProductIdentityMatch", "Yes"),
            "OCRQualityBand": feats.get("OCRQualityBand", "High"),
            "ClaimClass": t.ground_truth,
            "ReviewerDecision": t.reviewer_decision,
            "ReviewerNote": t.reviewer_note or "",
            "ReviewedAt": t.reviewed_at.isoformat() if t.reviewed_at else "",
        }
        records.append(row)

    if format.lower() == "json":
        return JSONResponse(content={"total_records": len(records), "data": records})

    # Output CSV format
    output = io.StringIO()
    if records:
        writer = csv.DictWriter(output, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)
    else:
        # Default header
        fieldnames = ["ClaimID"] + MODEL_14_FEATURES + ["ClaimClass", "ReviewerDecision", "ReviewerNote", "ReviewedAt"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

    output.seek(0)
    filename = f"warranty_retraining_dataset_14features_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get(
    "/retraining/dataset",
    summary="Get Retraining Records (JSON endpoint)",
)
def get_retraining_dataset_json(db: Session = Depends(get_db)):
    stmt = (
        select(WarrantyTicket)
        .where(WarrantyTicket.ground_truth.is_not(None))
        .order_by(WarrantyTicket.reviewed_at.desc())
    )
    tickets = db.scalars(stmt).all()
    records = []
    for t in tickets:
        feats = t.model_features or {}
        records.append({
            "ticket_id": t.ticket_id,
            "ClaimID": t.ticket_id,
            "product_type": t.product_type,
            "product_model": t.product_model,
            "usage_duration": t.usage_duration,
            "problem_category": t.problem_category,
            "problem_description": t.problem_description,
            "ai_prediction": t.ai_prediction,
            "ai_confidence": t.ai_confidence,
            "ground_truth": t.ground_truth,
            "reviewer_decision": t.reviewer_decision,
            "reviewer_note": t.reviewer_note,
            "reviewed_at": t.reviewed_at.isoformat() if t.reviewed_at else None,
            "model_features": feats,
            **feats,
        })
    return {
        "total": len(records),
        "total_records": len(records),
        "records": records,
        "data": records,
    }
