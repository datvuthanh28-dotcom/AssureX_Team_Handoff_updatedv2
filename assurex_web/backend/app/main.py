from app.warranty_routes import router as warranty_router
from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine, get_db
from app.ml.model_service import (
    GOOGLE_INFERENCE_STATUS,
    GOOGLE_MODEL_CONFIG,
    MODEL_NAME,
    MODEL_VERSION,
    predict_claim,
)
from app.models import AuditLog, Claim, CustomerAccount
from app.customer_routes import router as customer_router
from app.auth_routes import (
    record_audit,
    require_roles,
    router as auth_router,
    seed_default_admin,
    seed_default_reviewer,
)
from app.notification_routes import router as notification_router
from app.catalog_routes import router as catalog_router


app = FastAPI(
    title="AssureX Claim Engine API",
    version="1.0.0",
    description="Backend API for AssureX warranty claim classification.",
)


app.include_router(customer_router)
app.include_router(warranty_router)
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
        "full_name": "ALTER TABLE customer_accounts ADD COLUMN full_name VARCHAR(150)",
        "phone_number": "ALTER TABLE customer_accounts ADD COLUMN phone_number VARCHAR(30)",
        "address": "ALTER TABLE customer_accounts ADD COLUMN address VARCHAR(255)",
        "city": "ALTER TABLE customer_accounts ADD COLUMN city VARCHAR(100)",
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
            "google_model_name": (
                "ALTER TABLE claims ADD COLUMN google_model_name VARCHAR(100)"
            ),
            "google_model_version": (
                "ALTER TABLE claims ADD COLUMN google_model_version VARCHAR(100)"
            ),
            "google_inference_status": (
                "ALTER TABLE claims ADD COLUMN google_inference_status VARCHAR(50)"
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
            "python_model_name": (
                "ALTER TABLE customer_claim_decisions "
                "ADD COLUMN python_model_name VARCHAR(100)"
            ),
            "python_model_version": (
                "ALTER TABLE customer_claim_decisions "
                "ADD COLUMN python_model_version VARCHAR(64)"
            ),
            "gtm_model_version": (
                "ALTER TABLE customer_claim_decisions "
                "ADD COLUMN gtm_model_version VARCHAR(64)"
            ),
            "google_model_name": (
                "ALTER TABLE customer_claim_decisions "
                "ADD COLUMN google_model_name VARCHAR(100)"
            ),
            "google_model_version": (
                "ALTER TABLE customer_claim_decisions "
                "ADD COLUMN google_model_version VARCHAR(100)"
            ),
            "google_inference_status": (
                "ALTER TABLE customer_claim_decisions "
                "ADD COLUMN google_inference_status VARCHAR(50)"
            ),
            "google_prediction": (
                "ALTER TABLE customer_claim_decisions "
                "ADD COLUMN google_prediction VARCHAR(50)"
            ),
            "google_confidence": (
                "ALTER TABLE customer_claim_decisions "
                "ADD COLUMN google_confidence FLOAT"
            ),
            "confidence_difference": (
                "ALTER TABLE customer_claim_decisions "
                "ADD COLUMN confidence_difference FLOAT"
            ),
            "model_consistency_status": (
                "ALTER TABLE customer_claim_decisions "
                "ADD COLUMN model_consistency_status VARCHAR(50)"
            ),
        }
        for column_name, statement in decision_migrations.items():
            if column_name not in decision_columns:
                connection.execute(text(statement))

        table_names = set(inspect(engine).get_table_names())
        if "customer_claims" in table_names:
            cc_columns = {col["name"] for col in inspect(engine).get_columns("customer_claims")}
            cc_migrations = {
                "receipt_url": "ALTER TABLE customer_claims ADD COLUMN receipt_url VARCHAR(255)",
                "evidence_photo_url": "ALTER TABLE customer_claims ADD COLUMN evidence_photo_url VARCHAR(255)",
                "product_image_url": "ALTER TABLE customer_claims ADD COLUMN product_image_url VARCHAR(255)",
                "repair_report_url": "ALTER TABLE customer_claims ADD COLUMN repair_report_url VARCHAR(255)",
                "document_hashes": "ALTER TABLE customer_claims ADD COLUMN document_hashes JSON",
                "previous_repair_date": "ALTER TABLE customer_claims ADD COLUMN previous_repair_date VARCHAR(20)",
                "repair_center_name": "ALTER TABLE customer_claims ADD COLUMN repair_center_name VARCHAR(150)",
                "replaced_parts": "ALTER TABLE customer_claims ADD COLUMN replaced_parts VARCHAR(255)",
                "repair_outcome": "ALTER TABLE customer_claims ADD COLUMN repair_outcome VARCHAR(100)",
                "repair_cost": "ALTER TABLE customer_claims ADD COLUMN repair_cost FLOAT",
            }
            for col_name, stmt in cc_migrations.items():
                if col_name not in cc_columns:
                    connection.execute(text(stmt))

        if "registered_products" in table_names:
            rp_columns = {col["name"] for col in inspect(engine).get_columns("registered_products")}
            rp_migrations = {
                "purchase_price": "ALTER TABLE registered_products ADD COLUMN purchase_price FLOAT",
                "retailer": "ALTER TABLE registered_products ADD COLUMN retailer VARCHAR(150)",
            }
            for col_name, stmt in rp_migrations.items():
                if col_name not in rp_columns:
                    connection.execute(text(stmt))

        if "warranties" in table_names:
            w_columns = {col["name"] for col in inspect(engine).get_columns("warranties")}
            w_migrations = {
                "warranty_provider": "ALTER TABLE warranties ADD COLUMN warranty_provider VARCHAR(100) DEFAULT 'AssureX Official Care'",
                "warranty_type": "ALTER TABLE warranties ADD COLUMN warranty_type VARCHAR(50) DEFAULT 'Standard'",
                "coverage_conditions": "ALTER TABLE warranties ADD COLUMN coverage_conditions TEXT",
                "exclusions": "ALTER TABLE warranties ADD COLUMN exclusions TEXT",
                "service_center_details": "ALTER TABLE warranties ADD COLUMN service_center_details VARCHAR(255)",
            }
            for col_name, stmt in w_migrations.items():
                if col_name not in w_columns:
                    connection.execute(text(stmt))

    with SessionLocal() as db:
        seed_default_admin(db)
        seed_default_reviewer(db)


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
        google_model_name=result["google_model"]["model_name"],
        google_model_version=result["google_model"]["model_version"],
        google_inference_status=result["google_model"]["inference_status"],
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
        "python_model_name": result["model_name"],
        "created_at": claim.created_at,
        "google_inference": result["google_model"],
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
        "python_model_name": claim.model_name,
        "python_model_version": claim.python_model_version,
        "gtm_model_version": claim.gtm_model_version,
        "google_model_name": claim.google_model_name,
        "google_model_version": claim.google_model_version,
        "google_inference_status": claim.google_inference_status,
        "analysis_timestamp": claim.created_at,
        "python_model_version": claim.python_model_version,
        "gtm_model_version": claim.gtm_model_version,
        "analysis_timestamp": claim.created_at,
        "created_at": claim.created_at,
    }


@app.post("/api/claims/{claim_id}/analyze")
def analyze_claim(
    claim_id: str,
    _: CustomerAccount = Depends(
        require_roles("ADMIN", "SERVICE_CENTER", "REVIEWER")
    ),
    db: Session = Depends(get_db),
):
    claim = db.scalar(
        select(Claim).where(Claim.claim_id == claim_id)
    )
    if claim is None:
        raise HTTPException(
            status_code=404,
            detail=f"ClaimID {claim_id} not found.",
        )

    return JSONResponse(
        status_code=503,
        content={
            "claim_id": claim_id,
            "analysis_status": "google_model_not_connected",
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "python_model": {
                "name": MODEL_NAME,
                "version": MODEL_VERSION,
                "available": True,
            },
            "google_model": {
                "name": GOOGLE_MODEL_CONFIG.get("name"),
                "version": GOOGLE_MODEL_CONFIG.get("version"),
                "inference_status": GOOGLE_INFERENCE_STATUS,
                "prediction": None,
                "confidence": None,
            },
            "decision_engine_status": "not_run",
            "detail": (
                "The selected Google Teachable Machine model is not connected "
                "to runtime inference. No combined analysis or decision was created."
            ),
        },
    )

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
