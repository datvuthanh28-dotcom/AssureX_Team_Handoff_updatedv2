from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Claim(Base):
    __tablename__ = "claims"
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )
    claim_id: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    input_data: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )
    predicted_class: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    model_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    google_model_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    google_model_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    google_inference_status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    python_model_version: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    gtm_model_version: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


class CustomerClaim(Base):
    __tablename__ = "customer_claims"
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )
    claim_id: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    customer_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    product_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    serial_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    purchase_date: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    claim_amount: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    fault_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    problem_category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="Under Review",
        nullable=False,
    )
    receipt_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    evidence_photo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    product_image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    repair_report_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    document_hashes: Mapped[dict | None] = mapped_column(JSON, default=dict, nullable=True)
    previous_repair_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    repair_center_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    replaced_parts: Mapped[str | None] = mapped_column(String(255), nullable=True)
    repair_outcome: Mapped[str | None] = mapped_column(String(100), nullable=True)
    repair_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


class CustomerClaimDecision(Base):
    __tablename__ = "customer_claim_decisions"
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )
    claim_id: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    ml_prediction: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    ml_confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    probabilities: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )
    final_decision: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    requires_admin_review: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    decision_reasons: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    raw_input: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )
    model_features: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )
    derived_data: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )
    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    python_model_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    google_model_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    google_model_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    google_inference_status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    google_prediction: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    google_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    confidence_difference: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    model_consistency_status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    python_model_version: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    gtm_model_version: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    reviewer_decision: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    reviewer_comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    customer_confirmation: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )
    customer_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


class CustomerAccount(Base):
    __tablename__ = "customer_accounts"
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )
    email: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        index=True,
        nullable=False,
    )
    username: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=True,
    )
    role: Mapped[str] = mapped_column(
        String(30),
        default="CUSTOMER",
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    password_salt: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    full_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )
    phone_number: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )
    address: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


class CustomerSession(Base):
    __tablename__ = "customer_sessions"
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("customer_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )
    actor_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    actor_email: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    actor_role: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(
        String(80),
        index=True,
        nullable=False,
    )
    resource_type: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )
    resource_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    result: Mapped[str] = mapped_column(
        String(30),
        default="SUCCESS",
        nullable=False,
    )
    details: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
        nullable=False,
    )


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("customer_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(160),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    resource_type: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )
    resource_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
        nullable=False,
    )


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    brand: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    warranty_months: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


class RegisteredProduct(Base):
    __tablename__ = "registered_products"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("customer_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        index=True,
        nullable=False,
    )
    serial_number: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    purchase_date: Mapped[str] = mapped_column(String(20), nullable=False)
    purchase_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    retailer: Mapped[str | None] = mapped_column(String(150), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


class Warranty(Base):
    __tablename__ = "warranties"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    registered_product_id: Mapped[int] = mapped_column(
        ForeignKey("registered_products.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    start_date: Mapped[str] = mapped_column(String(20), nullable=False)
    end_date: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    warranty_provider: Mapped[str | None] = mapped_column(
        String(100), nullable=True, default="AssureX Official Care"
    )
    warranty_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, default="Standard"
    )
    coverage_conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    exclusions: Mapped[str | None] = mapped_column(Text, nullable=True)
    service_center_details: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


class ClaimAppeal(Base):
    __tablename__ = "claim_appeals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    claim_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="Pending")
    reviewer_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class WarrantyTicket(Base):
    __tablename__ = "warranty_tickets"
    ticket_id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        index=True,
    )
    product_type: Mapped[str] = mapped_column(String(50), nullable=False)
    product_model: Mapped[str] = mapped_column(String(100), nullable=False)
    order_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    purchase_date: Mapped[str] = mapped_column(String(20), nullable=False)
    usage_duration: Mapped[int] = mapped_column(Integer, nullable=False)
    problem_category: Mapped[str] = mapped_column(String(100), nullable=False)
    problem_description: Mapped[str] = mapped_column(Text, nullable=False)
    customer_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("customer_accounts.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    registered_product_id: Mapped[int | None] = mapped_column(
        ForeignKey("registered_products.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    raw_input: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="PENDING_AI", nullable=False)
    ai_prediction: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_features: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reviewer_decision: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ground_truth: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
