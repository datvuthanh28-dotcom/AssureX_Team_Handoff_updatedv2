from app.warranty_routes import router as warranty_router
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine, get_db
from app.ml.model_service import predict_claim
from app.models import AuditLog, Claim, CustomerAccount
from app.customer_routes import router as customer_router
from app.auth_routes import (
    record_audit,
    require_roles,
    router as auth_router,
    seed_default_admin,
)
from app.notification_routes import router as notification_router
from app.catalog_routes import router as catalog_router


app = FastAPI(
    title="AssureX Claim Engine API",
    version="1.0.0",
    description="Backend API for AssureX warranty claim classification.",
)


app.include_router(customer_router)
app.include_router(auth_router)
app.include_router(notification_router)
app.include_router(catalog_router)


@app.on_event("startup")
def create_database_tables():
    Base.metadata.create_all(bind=engine)
    columns = {
        column["name"]
        for column in inspect(engine).get_columns("customer_accounts")
    }
    migrations = {
        "username": "ALTER TABLE customer_accounts ADD COLUMN username VARCHAR(100)",
        "role": "ALTER TABLE customer_accounts ADD COLUMN role VARCHAR(30) NOT NULL DEFAULT 'CUSTOMER'",
        "is_active": "ALTER TABLE customer_accounts ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1",
    }
    with engine.begin() as connection:
        claim_columns = {
            column["name"]
            for column in inspect(engine).get_columns("claims")
        }
        claim_migrations = {
            "python_model_version": (
                "ALTER TABLE claims ADD COLUMN python_model_version VARCHAR(64)"
            ),
            "gtm_model_version": (
                "ALTER TABLE claims ADD COLUMN gtm_model_version VARCHAR(64)"
            ),
        }
        for column_name, statement in claim_migrations.items():
            if column_name not in claim_columns:
                connection.execute(text(statement))

        for column_name, statement in migrations.items():
            if column_name not in columns:
                connection.execute(text(statement))
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS "
                "ix_customer_accounts_username "
                "ON customer_accounts (username)"
            )
        )
        decision_columns = {
            column["name"]
            for column in inspect(engine).get_columns(
                "customer_claim_decisions"
            )
        }
        decision_migrations = {
            "python_model_version": (
                "ALTER TABLE customer_claim_decisions "
                "ADD COLUMN python_model_version VARCHAR(64)"
            ),
            "gtm_model_version": (
                "ALTER TABLE customer_claim_decisions "
                "ADD COLUMN gtm_model_version VARCHAR(64)"
            ),
        }
        for column_name, statement in decision_migrations.items():
            if column_name not in decision_columns:
                connection.execute(text(statement))

    with SessionLocal() as db:
        seed_default_admin(db)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=(
        r"http://(localhost|127\.0\.0\.1|192\.168\.1\.\d+):(5173|5174|5175)"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ClaimPredictRequest(BaseModel):
    claim_id: str
    input_data: dict[str, Any]


@app.get("/")
def root():
    return {
        "app": "AssureX Claim Engine API",
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
    }


@app.post("/api/claims/predict")
def predict(
    request: ClaimPredictRequest,
    account: CustomerAccount = Depends(
        require_roles("ADMIN", "SERVICE_CENTER")
    ),
    db: Session = Depends(get_db),
):
    existing_claim = db.scalar(
        select(Claim).where(
            Claim.claim_id == request.claim_id
        )
    )

    if existing_claim:
        raise HTTPException(
            status_code=409,
            detail=f"ClaimID {request.claim_id} already exists.",
        )

    try:
        result = predict_claim(request.input_data)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    claim = Claim(
        claim_id=request.claim_id,
        input_data=request.input_data,
        predicted_class=result["predicted_class"],
        confidence=result["confidence"],
        model_name=result["model_name"],
        python_model_version=result["model_version"],
        gtm_model_version=None,
    )

    db.add(claim)
    record_audit(
        db,
        account=account,
        action="MODEL_PREDICTION",
        resource_type="CLAIM",
        resource_id=claim.claim_id,
        details={
            "model": result["model_name"],
            "prediction": result["predicted_class"],
            "confidence": result["confidence"],
        },
    )
    db.commit()
    db.refresh(claim)

    return {
        "id": claim.id,
        "claim_id": claim.claim_id,
        "predicted_class": result["predicted_class"],
        "confidence": result["confidence"],
        "probabilities": result["probabilities"],
        "model_name": result["model_name"],
        "created_at": claim.created_at,
    }


@app.get("/api/claims")
def get_claims(
    _: CustomerAccount = Depends(
        require_roles("ADMIN", "SERVICE_CENTER", "REVIEWER")
    ),
    db: Session = Depends(get_db),
):
    claims = db.scalars(
        select(Claim).order_by(
            Claim.created_at.desc()
        )
    ).all()

    return [
        {
            "id": claim.id,
            "claim_id": claim.claim_id,
            "predicted_class": claim.predicted_class,
            "confidence": claim.confidence,
            "model_name": claim.model_name,
            "created_at": claim.created_at,
        }
        for claim in claims
    ]


@app.get("/api/claims/{claim_id}")
def get_claim_detail(
    claim_id: str,
    _: CustomerAccount = Depends(
        require_roles("ADMIN", "SERVICE_CENTER", "REVIEWER")
    ),
    db: Session = Depends(get_db),
):
    claim = db.scalar(
        select(Claim).where(
            Claim.claim_id == claim_id
        )
    )

    if claim is None:
        raise HTTPException(
            status_code=404,
            detail=f"ClaimID {claim_id} not found.",
        )

    return {
        "id": claim.id,
        "claim_id": claim.claim_id,
        "input_data": claim.input_data,
        "predicted_class": claim.predicted_class,
        "confidence": claim.confidence,
        "model_name": claim.model_name,
        "python_model_version": claim.python_model_version,
        "gtm_model_version": claim.gtm_model_version,
        "analysis_timestamp": claim.created_at,
        "python_model_version": claim.python_model_version,
        "gtm_model_version": claim.gtm_model_version,
        "analysis_timestamp": claim.created_at,
        "created_at": claim.created_at,
    }

app.include_router(warranty_router)


@app.get("/api/audit")
def get_audit_logs(
    _: CustomerAccount = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    entries = db.scalars(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(500)
    ).all()
    return [
        {
            "id": entry.id,
            "date": entry.created_at,
            "user": entry.actor_email,
            "role": entry.actor_role,
            "action": entry.action,
            "resource": entry.resource_type,
            "resource_id": entry.resource_id,
            "result": entry.result,
            "details": entry.details,
        }
        for entry in entries
    ]
