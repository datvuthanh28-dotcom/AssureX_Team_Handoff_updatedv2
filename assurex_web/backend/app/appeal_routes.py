from datetime import datetime
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ClaimAppeal, CustomerClaim, CustomerAccount, AuditLog
from app.auth_routes import require_roles, record_audit
from app.customer_routes import CustomerClaimStatusUpdate, get_decision, update_customer_claim_status

router = APIRouter(prefix="/api/appeals", tags=["Appeals"])

class AppealCreate(BaseModel):
    claim_id: str
    reason: str = Field(min_length=10, max_length=5000)

class AppealResolve(BaseModel):
    status: Literal["Approved", "Rejected"]
    reviewer_comment: str = Field(min_length=5, max_length=5000)


def serialize(appeal):
    return {key: getattr(appeal, key) for key in ("id", "claim_id", "reason", "status", "reviewer_comment", "created_at", "resolved_at")}

@router.get("")
def list_appeals(account=Depends(require_roles("ADMIN", "REVIEWER", "CUSTOMER")), db: Session = Depends(get_db)):
    query = select(ClaimAppeal).join(CustomerClaim, CustomerClaim.claim_id == ClaimAppeal.claim_id)
    if account.role == "CUSTOMER":
        query = query.where(CustomerClaim.email == account.email)
    return [serialize(row) for row in db.scalars(query.order_by(ClaimAppeal.created_at.desc())).all()]

@router.post("")
def create_appeal(payload: AppealCreate, account=Depends(require_roles("CUSTOMER")), db: Session = Depends(get_db)):
    claim = db.scalar(select(CustomerClaim).where(CustomerClaim.claim_id == payload.claim_id, CustomerClaim.email == account.email))
    if claim is None:
        raise HTTPException(404, "Claim not found.")
    decision = get_decision(db, claim.claim_id)
    invalid_awaiting_customer = (
        claim.status == "Under Review"
        and decision is not None
        and decision.final_decision == "Invalid Claim"
        and decision.customer_confirmation is None
    )
    if claim.status != "Rejected" and not invalid_awaiting_customer:
        raise HTTPException(409, "Only rejected claims or unconfirmed invalid results can be appealed.")
    if len(payload.reason.strip()) < 10:
        raise HTTPException(422, "Please provide at least 10 characters explaining your appeal.")
    if db.scalar(select(ClaimAppeal).where(ClaimAppeal.claim_id == claim.claim_id)):
        raise HTTPException(409, "An appeal already exists for this claim.")
    appeal = ClaimAppeal(claim_id=claim.claim_id, reason=payload.reason.strip())
    db.add(appeal)
    record_audit(db, account=account, action="APPEAL_SUBMITTED", resource_type="CLAIM", resource_id=claim.claim_id, details={"reason": appeal.reason})
    db.commit()
    db.refresh(appeal)
    return serialize(appeal)

@router.patch("/{appeal_id}")
def resolve_appeal(appeal_id: int, payload: AppealResolve, account=Depends(require_roles("ADMIN", "REVIEWER")), db: Session = Depends(get_db)):
    appeal = db.scalar(select(ClaimAppeal).where(ClaimAppeal.id == appeal_id))
    if not appeal:
        raise HTTPException(404, "Appeal not found.")
    if appeal.status != "Pending":
        raise HTTPException(409, "This appeal has already been resolved.")
    if len(payload.reviewer_comment.strip()) < 5:
        raise HTTPException(422, "A review explanation is required.")
    appeal.status = payload.status
    appeal.reviewer_comment = payload.reviewer_comment.strip()
    appeal.resolved_at = datetime.utcnow()
    record_audit(db, account=account, action="APPEAL_RESOLVED", resource_type="CLAIM", resource_id=appeal.claim_id, details=payload.model_dump())
    update_customer_claim_status(appeal.claim_id, CustomerClaimStatusUpdate(status=payload.status, reviewer_comment=appeal.reviewer_comment), account, db)
    return serialize(appeal)

@router.get("/feedback/export")
def export_feedback(account=Depends(require_roles("ADMIN")), db: Session = Depends(get_db)):
    # Human adjudications only. Predictions are never treated as ground truth.
    rows = []
    for claim in db.scalars(select(CustomerClaim).where(CustomerClaim.status.in_(["Approved", "Rejected"]))).all():
        latest = db.scalar(select(AuditLog).where(AuditLog.resource_id == claim.claim_id, AuditLog.resource_type == "CLAIM", AuditLog.action.in_(("REVIEWER_ACTION", "CUSTOMER_RESULT_CONFIRMED"))).order_by(AuditLog.created_at.desc(), AuditLog.id.desc()))
        pending = db.scalar(select(ClaimAppeal).where(ClaimAppeal.claim_id == claim.claim_id, ClaimAppeal.status == "Pending"))
        if latest is None or pending or latest.details.get("status") != claim.status:
            continue
        rows.append({"claim_id": claim.claim_id, "reviewed_at": latest.created_at.isoformat(), "label": "Valid Claim" if claim.status == "Approved" else "Invalid Claim", "label_source": "Customer" if latest.action == "CUSTOMER_RESULT_CONFIRMED" else "Reviewer", "input": {column.name: getattr(claim, column.name) for column in CustomerClaim.__table__.columns if column.name not in ("email", "customer_name")}})
    return {"created_at": datetime.utcnow().isoformat(), "status": "reviewed_feedback_export", "training_started": False, "records": rows}
