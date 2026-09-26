from datetime import datetime
from math import isnan
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    AuditLog,
    CustomerAccount,
    CustomerClaim,
    CustomerClaimDecision,
)
from app.auth_routes import get_current_customer, record_audit, require_roles
from app.notification_routes import add_notification
from app.ml.model_service import predict_claim
from app.ml.feature_service import build_claim_features
from app.ml.decision_service import apply_business_rules
from app.ml.document_compare_service import compare_warranty_data
from app.ocr.ocr_service import extract_warranty_image


router = APIRouter(
    prefix="/api/customer/claims",
    tags=["Customer Claims"],
)


class CustomerClaimCreate(BaseModel):
    customer_name: str = Field(
        min_length=2,
        max_length=150,
    )

    email: str = Field(
        min_length=3,
        max_length=150,
    )

    product_name: str = Field(
        min_length=1,
        max_length=150,
    )

    model_number: str | None = None

    serial_number: str = Field(
        min_length=1,
        max_length=100,
    )

    evidence_serial_number: str | None = None
    evidence_model_number: str | None = None

    purchase_date: str
    fault_date: str | None = None

    warranty_duration_months: int | None = None
    extended_warranty: str | None = "No"

    damage_type: str | None = None

    claim_amount: float | None = Field(
        default=None,
        gt=0,
    )

    fault_description: str = Field(
        min_length=5,
    )

    receipt_available: str | None = None
    warranty_card_available: str | None = None
    product_image_available: str | None = None
    serial_evidence_available: str | None = None
    fault_evidence_available: str | None = None

    previous_repair: str | None = "No"
    repair_count: int = 0
    repair_report_available: str | None = None
    repair_authorized: str | None = None

    ocr_confidence: float | None = None
    document_duplicate_indicator: str | None = None

    warranty_document_id: str | None = None
    warranty_ocr_data: dict[str, Any] | None = None
    warranty_ocr_confidence: float | None = None


class CustomerClaimStatusUpdate(BaseModel):
    status: Literal[
        "Draft",
        "Submitted",
        "Under Evaluation",
        "Additional Information Required",
        "Manual Review",
        "Under Review",
        "Approved",
        "Rejected",
        "Closed",
    ]

    reviewer_comment: str | None = None


def json_safe(value: Any):
    if isinstance(value, dict):
        return {
            key: json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            json_safe(item)
            for item in value
        ]

    if isinstance(value, float) and isnan(value):
        return None

    return value



WARRANTY_UPLOAD_DIR = Path(
    "app/uploads/warranty_cards"
)


def load_warranty_document_ocr(
    document_id: str,
):
    safe_id = str(
        document_id
    ).strip()

    if (
        not safe_id.startswith("WAR-")
        or "/" in safe_id
        or "\\" in safe_id
        or ".." in safe_id
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid warranty "
                "document ID."
            ),
        )

    document_path = None

    for suffix in (
        ".jpg",
        ".png",
        ".webp",
    ):
        candidate = (
            WARRANTY_UPLOAD_DIR
            / f"{safe_id}{suffix}"
        )

        if candidate.exists():
            document_path = candidate
            break

    if document_path is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Uploaded warranty "
                "document was not found."
            ),
        )

    try:
        return extract_warranty_image(
            document_path
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                "Warranty document "
                f"could not be verified: {exc}"
            ),
        ) from exc


def get_decision(
    db: Session,
    claim_id: str,
):
    return db.scalar(
        select(CustomerClaimDecision).where(
            CustomerClaimDecision.claim_id
            == claim_id
        )
    )


def serialize_claim(
    claim: CustomerClaim,
    db: Session,
):
    decision = get_decision(
        db,
        claim.claim_id,
    )

    result = {
        "id": claim.id,
        "claim_id": claim.claim_id,
        "customer_name": claim.customer_name,
        "email": claim.email,
        "product_name": claim.product_name,
        "serial_number": claim.serial_number,
        "purchase_date": claim.purchase_date,
        "claim_amount": (
            None
            if claim.claim_amount == 0
            else claim.claim_amount
        ),
        "fault_description":
            claim.fault_description,
        "status": claim.status,
        "created_at": claim.created_at,
    }

    if decision is None:
        result["decision"] = None
        return result

    result["decision"] = {
        "ml_prediction":
            decision.ml_prediction,

        "ml_confidence":
            decision.ml_confidence,

        "probabilities":
            decision.probabilities,

        "final_decision":
            decision.final_decision,

        "requires_admin_review":
            bool(
                decision.requires_admin_review
            ),

        "decision_reasons":
            decision.decision_reasons,

        "model_name":
            decision.model_name,

        "python_model_name":
            decision.python_model_name or decision.model_name,

        "python_model_version":
            decision.python_model_version,

        "gtm_model_version":
            decision.gtm_model_version,

        "google_model_name":
            decision.google_model_name,

        "google_model_version":
            decision.google_model_version,

        "google_inference_status":
            decision.google_inference_status,

        "google_prediction":
            decision.google_prediction,

        "google_confidence":
            decision.google_confidence,

        "confidence_difference":
            decision.confidence_difference,

        "model_consistency_status":
            decision.model_consistency_status,

        "analysis_timestamp":
            decision.created_at,

        "raw_input":
            decision.raw_input,

        "model_features":
            decision.model_features,

        "derived_data":
            decision.derived_data,

        "reviewer_decision":
            decision.reviewer_decision,

        "reviewer_comment":
            decision.reviewer_comment,

        "reviewed_at":
            decision.reviewed_at,
    }

    return result


@router.post("")
def submit_customer_claim(
    payload: CustomerClaimCreate,
    account: CustomerAccount = Depends(require_roles("CUSTOMER")),
    db: Session = Depends(get_db),
):
    payload = payload.model_copy(
        update={"email": account.email}
    )
    claim_id = (
        "CUST-"
        + datetime.utcnow().strftime(
            "%Y%m%d%H%M%S"
        )
        + "-"
        + uuid4().hex[:6].upper()
    )

    raw_input = payload.model_dump()

    # ---------------------------------------------
    # WARRANTY DOCUMENT VERIFICATION
    #
    # Never trust OCR values returned by the
    # browser. If a document_id exists, OCR the
    # server-side uploaded image again.
    # ---------------------------------------------

    warranty_ocr_result = None
    warranty_comparison = None

    if payload.warranty_document_id:
        warranty_ocr_result = (
            load_warranty_document_ocr(
                payload.warranty_document_id
            )
        )

        extracted = (
            warranty_ocr_result[
                "extracted_data"
            ]
            or {}
        )

        # Replace browser-supplied OCR values
        # with server-side OCR values.
        raw_input[
            "warranty_ocr_data"
        ] = extracted

        raw_input[
            "warranty_ocr_confidence"
        ] = warranty_ocr_result[
            "ocr_confidence"
        ]

        # Production ML feature.
        raw_input[
            "ocr_confidence"
        ] = warranty_ocr_result[
            "ocr_confidence"
        ]

        raw_input[
            "warranty_card_available"
        ] = "Yes"

        # Use values actually extracted from
        # the uploaded warranty document as
        # verification evidence.
        if extracted.get(
            "serial_number"
        ):
            raw_input[
                "evidence_serial_number"
            ] = extracted[
                "serial_number"
            ]

            raw_input[
                "serial_evidence_available"
            ] = "Yes"

        if extracted.get(
            "model_number"
        ):
            raw_input[
                "evidence_model_number"
            ] = extracted[
                "model_number"
            ]

        warranty_comparison = (
            compare_warranty_data(
                extracted,
                raw_input,
            )
        )

        raw_input[
            "warranty_document_mismatch"
        ] = warranty_comparison[
            "has_mismatch"
        ]

        raw_input[
            "warranty_document_mismatch_fields"
        ] = warranty_comparison[
            "mismatch_fields"
        ]

        raw_input[
            "warranty_document_comparison"
        ] = warranty_comparison[
            "comparisons"
        ]

    # ---------------------------------------------
    # PRIOR CLAIM HISTORY
    # ---------------------------------------------

    prior_claim_count = db.scalar(
        select(func.count())
        .select_from(CustomerClaim)
        .where(
            CustomerClaim.serial_number
            == payload.serial_number
        )
    ) or 0

    # ---------------------------------------------
    # DUPLICATE DETECTION
    # ---------------------------------------------

    duplicate = db.scalar(
        select(CustomerClaim).where(
            CustomerClaim.email
            == payload.email,

            CustomerClaim.serial_number
            == payload.serial_number,

            CustomerClaim.fault_description
            == payload.fault_description,
        )
    )

    duplicate_claim = (
        duplicate is not None
    )

    # ---------------------------------------------
    # NORMALIZE REPAIR VALUES
    # ---------------------------------------------

    if (
        str(payload.previous_repair)
        .strip()
        .lower()
        == "no"
    ):
        raw_input["repair_authorized"] = (
            "Not Applicable"
        )

        raw_input[
            "repair_report_available"
        ] = "Not Applicable"

    # ---------------------------------------------
    # FEATURE BUILDER
    # ---------------------------------------------

    feature_result = build_claim_features(
        raw_input,
        prior_claim_count=prior_claim_count,
        duplicate_claim=duplicate_claim,
    )

    model_features = dict(
        feature_result["model_features"]
    )

    rule_data = dict(
        feature_result["rule_data"]
    )

    if (
        warranty_comparison
        and warranty_comparison[
            "has_mismatch"
        ]
    ):
        mismatch_fields = (
            warranty_comparison[
                "mismatch_fields"
            ]
        )

        rule_data[
            "WarrantyDocumentMismatchIndicator"
        ] = "Yes"

        rule_data[
            "WarrantyDocumentMismatchFields"
        ] = mismatch_fields

        rule_data[
            "DocumentContradictionIndicator"
        ] = "Yes"

        # Feed detected contradiction into
        # the existing production feature too.
        model_features[
            "ContradictionIndicator"
        ] = "Yes"

    else:
        rule_data[
            "WarrantyDocumentMismatchIndicator"
        ] = "No"

        rule_data[
            "WarrantyDocumentMismatchFields"
        ] = []

    # ---------------------------------------------
    # PYTHON ML
    # ---------------------------------------------

    prediction = predict_claim(
        model_features
    )

    # ---------------------------------------------
    # DECISION ENGINE
    # ---------------------------------------------

    decision_result = apply_business_rules(
        rule_data,
        prediction["predicted_class"],
        prediction["confidence"],
    )

    google_model = prediction["google_model"]
    if google_model["inference_status"] != "connected":
        reason = "Google model inference is not connected"
        if reason not in decision_result["decision_reasons"]:
            decision_result["decision_reasons"].append(reason)
        if decision_result["final_decision"] != "Invalid Claim":
            decision_result["final_decision"] = "Manual Review"
            decision_result["customer_status"] = "Under Review"
            decision_result["requires_admin_review"] = True

    # ---------------------------------------------
    # CUSTOMER STATUS
    #
    # Valid  -> Approved
    # Invalid -> Rejected
    # Manual -> Under Review
    # ---------------------------------------------

    customer_status = (
        "Rejected"
        if decision_result["final_decision"] == "Invalid Claim"
        else "Manual Review"
        if decision_result["requires_admin_review"]
        else decision_result["customer_status"]
    )

    claim = CustomerClaim(
        claim_id=claim_id,
        customer_name=payload.customer_name,
        email=payload.email,
        product_name=payload.product_name,
        serial_number=payload.serial_number,
        purchase_date=payload.purchase_date,
        claim_amount=(
            payload.claim_amount
            if payload.claim_amount is not None
            else 0.0
        ),
        fault_description=
            payload.fault_description,
        status=customer_status,
    )

    db.add(claim)
    db.flush()

    derived_data = dict(
        feature_result["derived"]
    )
    derived_data["google_model"] = {
        "model_name": google_model["model_name"],
        "model_version": google_model["model_version"],
        "inference_status": google_model["inference_status"],
    }

    if warranty_ocr_result:
        derived_data[
            "warranty_document"
        ] = {
            "document_id":
                payload.warranty_document_id,

            "ocr_confidence":
                warranty_ocr_result[
                    "ocr_confidence"
                ],

            "extracted_data":
                warranty_ocr_result[
                    "extracted_data"
                ],

            "comparison":
                warranty_comparison,
        }

    decision_record = CustomerClaimDecision(
        claim_id=claim_id,

        ml_prediction=
            prediction["predicted_class"],

        ml_confidence=
            prediction["confidence"],

        probabilities=json_safe(
            prediction["probabilities"]
        ),

        final_decision=
            decision_result[
                "final_decision"
            ],

        requires_admin_review=(
            1
            if decision_result[
                "requires_admin_review"
            ]
            else 0
        ),

        decision_reasons=json_safe(
            decision_result[
                "decision_reasons"
            ]
        ),

        raw_input=json_safe(
            raw_input
        ),

        model_features=json_safe(
            model_features
        ),

        derived_data=json_safe(
            derived_data
        ),

        model_name=
            prediction["model_name"],

        python_model_name=
            prediction["model_name"],

        python_model_version=
            prediction["model_version"],

        gtm_model_version=None,

        google_model_name=
            google_model["model_name"],

        google_model_version=
            google_model["model_version"],

        google_inference_status=
            google_model["inference_status"],

        google_prediction=None,

        google_confidence=None,

        confidence_difference=None,

        model_consistency_status=(
            "Uncertain Result"
            if google_model["inference_status"] != "connected"
            else None
        ),
    )

    db.add(decision_record)

    record_audit(
        db,
        account=account,
        action="CLAIM_SUBMITTED",
        resource_type="CLAIM",
        resource_id=claim_id,
        details={
            "status": customer_status,
            "python_prediction": prediction["predicted_class"],
            "python_confidence": prediction["confidence"],
            "python_model_version": prediction["model_version"],
            "google_model_name": google_model["model_name"],
            "google_model_version": google_model["model_version"],
            "google_inference_status": google_model["inference_status"],
            "final_decision": decision_result["final_decision"],
            "decision_reasons": decision_result["decision_reasons"],
        },
    )

    add_notification(
        db,
        account_id=account.id,
        title="Claim received",
        message=f"Claim {claim_id} was received with status {customer_status}.",
        resource_type="CLAIM",
        resource_id=claim_id,
    )

    if decision_result["requires_admin_review"]:
        reviewers = db.scalars(
            select(CustomerAccount).where(
                CustomerAccount.role.in_(("ADMIN", "REVIEWER")),
                CustomerAccount.is_active.is_(True),
            )
        ).all()
        for reviewer in reviewers:
            add_notification(
                db,
                account_id=reviewer.id,
                title="Manual review required",
                message=f"Claim {claim_id} was routed for manual review.",
                resource_type="CLAIM",
                resource_id=claim_id,
            )

    db.commit()
    db.refresh(claim)

    return serialize_claim(
        claim,
        db,
    )


@router.get("")
def get_customer_claims(
    email: str | None = Query(
        default=None
    ),

    status: str | None = Query(
        default=None
    ),

    search: str | None = Query(
        default=None
    ),

    requires_review: bool | None = Query(
        default=None
    ),

    account: CustomerAccount = Depends(
        require_roles("CUSTOMER", "SERVICE_CENTER", "REVIEWER", "ADMIN")
    ),

    db: Session = Depends(get_db),
):
    statement = select(CustomerClaim)

    if account.role == "CUSTOMER":
        statement = statement.where(
            CustomerClaim.email == account.email
        )
    elif email:
        statement = statement.where(
            CustomerClaim.email == email
        )

    if status:
        statement = statement.where(
            CustomerClaim.status == status
        )

    if search:
        term = f"%{search}%"

        statement = statement.where(
            or_(
                CustomerClaim.claim_id.ilike(
                    term
                ),
                CustomerClaim.customer_name.ilike(
                    term
                ),
                CustomerClaim.email.ilike(
                    term
                ),
                CustomerClaim.product_name.ilike(
                    term
                ),
                CustomerClaim.serial_number.ilike(
                    term
                ),
            )
        )

    statement = statement.order_by(
        CustomerClaim.created_at.desc()
    )

    claims = db.scalars(
        statement
    ).all()

    output = [
        serialize_claim(
            claim,
            db,
        )
        for claim in claims
    ]

    if requires_review is not None:
        output = [
            claim
            for claim in output
            if bool(
                claim.get("decision")
                and claim["decision"].get(
                    "requires_admin_review"
                )
            )
            == requires_review
        ]

    return output


@router.get("/stats")
def get_customer_claim_stats(
    email: str | None = Query(
        default=None
    ),

    account: CustomerAccount = Depends(
        require_roles("CUSTOMER", "SERVICE_CENTER", "REVIEWER", "ADMIN")
    ),

    db: Session = Depends(get_db),
):
    statement = select(CustomerClaim)

    if account.role == "CUSTOMER":
        statement = statement.where(
            CustomerClaim.email == account.email
        )
    elif email:
        statement = statement.where(
            CustomerClaim.email == email
        )

    claims = db.scalars(
        statement
    ).all()

    serialized = [
        serialize_claim(
            claim,
            db,
        )
        for claim in claims
    ]

    return {
        "total": len(serialized),

        "under_review": sum(
            claim["status"] in {"Under Review", "Manual Review"}
            for claim in serialized
        ),

        "approved": sum(
            claim["status"]
            == "Approved"
            for claim in serialized
        ),

        "rejected": sum(
            claim["status"]
            == "Rejected"
            for claim in serialized
        ),

        "manual_review": sum(
            bool(
                claim.get("decision")
                and claim["decision"].get(
                    "requires_admin_review"
                )
            )
            for claim in serialized
        ),
    }


@router.get("/{claim_id}")
def get_customer_claim_detail(
    claim_id: str,
    account: CustomerAccount = Depends(
        require_roles("CUSTOMER", "SERVICE_CENTER", "REVIEWER", "ADMIN")
    ),
    db: Session = Depends(get_db),
):
    claim = db.scalar(
        select(CustomerClaim).where(
            CustomerClaim.claim_id
            == claim_id
        )
    )

    if claim is None:
        raise HTTPException(
            status_code=404,
            detail="Claim not found.",
        )

    if account.role == "CUSTOMER" and claim.email != account.email:
        raise HTTPException(status_code=404, detail="Claim not found.")

    return serialize_claim(
        claim,
        db,
    )


@router.get("/{claim_id}/history")
def get_customer_claim_history(
    claim_id: str,
    account: CustomerAccount = Depends(
        require_roles("CUSTOMER", "SERVICE_CENTER", "REVIEWER", "ADMIN")
    ),
    db: Session = Depends(get_db),
):
    claim = db.scalar(
        select(CustomerClaim).where(
            CustomerClaim.claim_id == claim_id
        )
    )
    if claim is None or (
        account.role == "CUSTOMER" and claim.email != account.email
    ):
        raise HTTPException(status_code=404, detail="Claim not found.")

    entries = db.scalars(
        select(AuditLog)
        .where(
            AuditLog.resource_type == "CLAIM",
            AuditLog.resource_id == claim_id,
        )
        .order_by(AuditLog.created_at.asc())
    ).all()
    return [
        {
            "date": entry.created_at,
            "user": entry.actor_email,
            "role": entry.actor_role,
            "action": entry.action,
            "result": entry.result,
            "details": entry.details,
        }
        for entry in entries
    ]


@router.patch("/{claim_id}/status")
def update_customer_claim_status(
    claim_id: str,
    payload: CustomerClaimStatusUpdate,
    account: CustomerAccount = Depends(
        require_roles("ADMIN", "REVIEWER")
    ),
    db: Session = Depends(get_db),
):
    claim = db.scalar(
        select(CustomerClaim).where(
            CustomerClaim.claim_id
            == claim_id
        )
    )

    if claim is None:
        raise HTTPException(
            status_code=404,
            detail="Claim not found.",
        )

    decision = get_decision(
        db,
        claim_id,
    )

    previous_status = claim.status
    claim.status = payload.status

    if decision is not None:
        decision.reviewer_decision = payload.status
        decision.reviewed_at = datetime.utcnow()
        decision.reviewer_comment = (
            payload.reviewer_comment
        )

    record_audit(
        db,
        account=account,
        action="REVIEWER_ACTION",
        resource_type="CLAIM",
        resource_id=claim_id,
        details={
            "previous_status": previous_status,
            "status": payload.status,
            "reviewer_comment": payload.reviewer_comment,
        },
    )

    customer = db.scalar(
        select(CustomerAccount).where(
            CustomerAccount.email == claim.email,
            CustomerAccount.role == "CUSTOMER",
            CustomerAccount.is_active.is_(True),
        )
    )
    if customer is not None:
        add_notification(
            db,
            account_id=customer.id,
            title="Claim status updated",
            message=f"Claim {claim_id} status changed to {payload.status}.",
            resource_type="CLAIM",
            resource_id=claim_id,
        )

    db.commit()
    db.refresh(claim)

    return serialize_claim(
        claim,
        db,
    )
