from datetime import date, datetime
import csv
import io
import re
from typing import Any, Literal
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import WarrantyTicket
from app.ml.model_service import MODEL_14_FEATURES, predict_claim

router = APIRouter(
    prefix="/api",
    tags=["Warranty Claim Management System"],
)

# Allowed Product Types according to SRS / Specification
ALLOWED_PRODUCT_TYPES = {
    "Laptop",
    "Smartphone",
    "Tablet",
    "Monitor",
    "Printer",
    "Other",
}

# ==============================================================================
# PYDANTIC SCHEMAS - 14 FINAL ML FEATURES
# ==============================================================================

class WarrantyClaimCreatePayload(BaseModel):
    # Identifying Product Information (Optional context)
    product_type: str | None = Field(default="Laptop", description="Allowed: Laptop, Smartphone, Tablet, Monitor, Printer, Other")
    product_model: str | None = Field(default="Standard Equipment", description="Product model or order description")
    order_code: str | None = Field(default=None, description="Optional Order Code or Serial")
    purchase_date: str | None = Field(default=None, description="YYYY-MM-DD")
    usage_duration: int | None = Field(default=1, description="Usage duration in months")
    problem_category: str | None = Field(default="Hardware Component", description="Problem category")
    problem_description: str | None = Field(default=None, description="Optional description of the issue")

    # ==========================================================================
    # THE 14 FEATURES FINALIZED DURING MODEL TRAINING (V3 GRADIENT BOOSTING)
    # ==========================================================================
    # Group 1: Product & Identity Verification
    ProductIdentityMatch: str = Field(default="Yes", description="Product identity match: Yes, No")
    SerialNumberMatch: str = Field(default="Yes", description="Serial number match: Yes, No, Unknown")
    ProductModelConsistent: str = Field(default="Yes", description="Model consistent: Yes, No")

    # Group 2: Warranty Status & Coverage
    WarrantyRemainingDays: float = Field(default=180.0, description="Remaining days under warranty coverage")
    FaultCovered: str = Field(default="Yes", description="Fault covered by policy: Yes, No, Unknown")
    ClaimReportingDelayDays: float = Field(default=5.0, ge=0.0, description="Delay days before reporting issue")
    ClaimReportingWithinPeriod: str = Field(default="Yes", description="Reporting within period: Yes, No, Unknown")

    # Group 3: Repair History & Integrity
    RepairAuthorized: str = Field(default="Not Applicable", description="Authorized repair: Yes, No, Not Applicable, Unknown")
    DuplicateClaimIndicator: str = Field(default="No", description="Duplicate claim: Yes, No")
    ContradictionIndicator: str = Field(default="No", description="Contradictory evidence: Yes, No")

    # Group 4: Documents & OCR Quality
    RequiredDocumentsComplete: str = Field(default="Yes", description="Required documents complete: Yes, No, Unknown")
    MissingDocumentCount: float = Field(default=0.0, ge=0.0, description="Count of missing documents")
    OCRConfidence: float = Field(default=0.90, ge=0.0, le=1.0, description="OCR document confidence: 0.0 to 1.0")
    OCRQualityBand: str = Field(default="High", description="OCR quality band: High, Medium, Low, Missing")


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

@router.post(
    "/warranty/claims",
    status_code=status.HTTP_201_CREATED,
    summary="Customer: Create Warranty Claim Ticket via 14-Feature Form",
)
def create_warranty_claim(
    payload: WarrantyClaimCreatePayload,
    db: Session = Depends(get_db),
):
    """
    1. Customer fills the form with the 14 features.
    2. System validates input data.
    3. Ticket is created with status PENDING_AI.
    4. 14 features are sent to the AI Model.
    5. Result enqueues ticket for Reviewer as WAITING_REVIEW.
    """
    # 1. Extract and sanitize 14 features
    features_14 = extract_14_features(payload)

    # Validate numbers
    if features_14["OCRConfidence"] < 0 or features_14["OCRConfidence"] > 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"OCRConfidence": "OCR Confidence must be between 0.0 and 1.0"},
        )
    if features_14["ClaimReportingDelayDays"] < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"ClaimReportingDelayDays": "Claim Reporting Delay Days cannot be negative."},
        )

    # 2. Generate unique Ticket ID
    ticket_id = f"TCK-{uuid.uuid4().hex[:8].upper()}"

    p_type = payload.product_type if payload.product_type in ALLOWED_PRODUCT_TYPES else "Laptop"
    p_model = (payload.product_model or "Standard Device").strip()
    p_date = payload.purchase_date or date.today().isoformat()
    duration = int(payload.usage_duration or 1)
    prob_cat = payload.problem_category or "Hardware Issue"
    prob_desc = payload.problem_description or (
        f"Claim with 14 features: FaultCovered={features_14['FaultCovered']}, "
        f"WarrantyDays={features_14['WarrantyRemainingDays']}, MissingDocs={features_14['MissingDocumentCount']}"
    )

    ticket = WarrantyTicket(
        ticket_id=ticket_id,
        product_type=p_type,
        product_model=p_model,
        order_code=payload.order_code,
        purchase_date=p_date,
        usage_duration=duration,
        problem_category=prob_cat,
        problem_description=prob_desc,
        status="PENDING_AI",
        model_features=features_14,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    # 3. Call AI Prediction Engine with the 14 features
    try:
        ai_res = execute_ai_prediction_14(features_14)
        ticket.ai_prediction = ai_res["prediction"]
        ticket.ai_confidence = ai_res["confidence"]
        ticket.status = "WAITING_REVIEW"
        ticket.ai_error_message = None
    except Exception as exc:
        ticket.status = "AI_ERROR"
        ticket.ai_error_message = f"AI Prediction Failed: {str(exc)}"

    db.commit()
    db.refresh(ticket)

    return {
        "success": True,
        "message": "Warranty ticket submitted and evaluated by AI successfully.",
        "ticket": {
            "ticket_id": ticket.ticket_id,
            "status": ticket.status,
            "product_type": ticket.product_type,
            "product_model": ticket.product_model,
            "purchase_date": ticket.purchase_date,
            "usage_duration": ticket.usage_duration,
            "problem_category": ticket.problem_category,
            "problem_description": ticket.problem_description,
            "model_features": ticket.model_features or features_14,
            "ai_prediction": ticket.ai_prediction,
            "ai_confidence": ticket.ai_confidence,
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
            "status": t.status,
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
def get_ticket_detail(ticket_id: str, db: Session = Depends(get_db)):
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
            "status": ticket.status,
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

