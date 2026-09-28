from calendar import monthrange
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth_routes import record_audit, require_roles
from app.database import get_db
from app.models import (
    CustomerAccount,
    CustomerClaim,
    Product,
    RegisteredProduct,
    Warranty,
)
from app.ml.feature_service import WARRANTY_POLICY


router = APIRouter(tags=["Products and Warranties"])


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    category: str = Field(min_length=1, max_length=100)
    brand: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=100)
    warranty_months: int = Field(gt=0, le=120)


class ProductRegister(BaseModel):
    product_id: int
    serial_number: str = Field(min_length=1, max_length=100)
    purchase_date: date
    purchase_price: float | None = Field(default=None, ge=0)
    retailer: str | None = Field(default=None, max_length=150)


class ActiveChange(BaseModel):
    is_active: bool


def add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def serialize_product(product: Product, db: Session) -> dict:
    registered_count = db.scalar(
        select(func.count()).select_from(RegisteredProduct).where(
            RegisteredProduct.product_id == product.id,
            RegisteredProduct.is_active.is_(True),
        )
    ) or 0
    active_claims = db.scalar(
        select(func.count())
        .select_from(CustomerClaim)
        .join(
            RegisteredProduct,
            RegisteredProduct.serial_number == CustomerClaim.serial_number,
        )
        .where(
            RegisteredProduct.product_id == product.id,
            CustomerClaim.status.not_in(("Approved", "Rejected", "Closed")),
        )
    ) or 0
    return {
        "id": product.id,
        "product_code": f"PRD-{product.id:04d}",
        "name": product.name,
        "category": product.category,
        "brand": product.brand,
        "model": product.model,
        "warranty_months": product.warranty_months,
        "registered_customers": registered_count,
        "active_claims": active_claims,
        "is_active": product.is_active,
        "created_at": product.created_at,
    }


@router.get("/api/products")
def list_products(
    account: CustomerAccount = Depends(
        require_roles("CUSTOMER", "SERVICE_CENTER", "REVIEWER", "ADMIN")
    ),
    db: Session = Depends(get_db),
):
    statement = select(Product)
    if account.role == "CUSTOMER":
        statement = statement.where(Product.is_active.is_(True))
    products = db.scalars(statement.order_by(Product.name.asc())).all()
    return [serialize_product(product, db) for product in products]


@router.get("/api/warranty-policies")
def list_warranty_policies(
    _: CustomerAccount = Depends(
        require_roles("CUSTOMER", "SERVICE_CENTER", "REVIEWER", "ADMIN")
    ),
):
    """Return customer-facing summaries from the same policy source as the decision engine."""
    common = WARRANTY_POLICY.get("common", {})
    common_exclusions = common.get("common_excluded_causes", [])
    summaries = {}
    for category, policy in WARRANTY_POLICY.get("categories", {}).items():
        summaries[category] = {
            "category": category,
            "policy_version": WARRANTY_POLICY.get("policy_version"),
            "warranty_months": policy.get("standard_warranty_months"),
            "covered_faults": policy.get("potentially_covered_faults", []),
            "excluded_causes": common_exclusions + policy.get("additional_excluded_causes", []),
            "required_evidence": policy.get("required_evidence", []),
            "installation_required": policy.get("installation_required", False),
        }
    home_appliance_categories = ["Refrigerator", "Washing Machine", "Air Conditioner"]
    home_appliance_policies = [
        WARRANTY_POLICY.get("categories", {}).get(category, {})
        for category in home_appliance_categories
    ]
    if home_appliance_policies:
        summaries["Appliance"] = {
            "category": "Appliance",
            "policy_version": WARRANTY_POLICY.get("policy_version"),
            "warranty_months": 24,
            "covered_faults": sorted({
                fault
                for policy in home_appliance_policies
                for fault in policy.get("potentially_covered_faults", [])
            }),
            "excluded_causes": sorted({
                cause
                for policy in home_appliance_policies
                for cause in common_exclusions + policy.get("additional_excluded_causes", [])
            }),
            "required_evidence": sorted({
                item
                for policy in home_appliance_policies
                for item in policy.get("required_evidence", [])
            }),
            "installation_required": any(
                policy.get("installation_required", False)
                for policy in home_appliance_policies
            ),
        }
    return summaries


@router.post("/api/products", status_code=201)
def create_product(
    payload: ProductCreate,
    account: CustomerAccount = Depends(require_roles("ADMIN", "SERVICE_CENTER")),
    db: Session = Depends(get_db),
):
    product = Product(**payload.model_dump())
    db.add(product)
    db.flush()
    record_audit(
        db,
        account=account,
        action="PRODUCT_CREATED",
        resource_type="PRODUCT",
        resource_id=str(product.id),
    )
    db.commit()
    db.refresh(product)
    return serialize_product(product, db)


@router.get("/api/products/registered")
def list_registered_products(
    account: CustomerAccount = Depends(
        require_roles("CUSTOMER", "SERVICE_CENTER", "REVIEWER", "ADMIN")
    ),
    db: Session = Depends(get_db),
):
    statement = (
        select(RegisteredProduct, Product, Warranty)
        .join(Product, Product.id == RegisteredProduct.product_id)
        .outerjoin(Warranty, Warranty.registered_product_id == RegisteredProduct.id)
    )
    if account.role == "CUSTOMER":
        statement = statement.where(RegisteredProduct.account_id == account.id)

    rows = db.execute(statement.order_by(RegisteredProduct.created_at.desc())).all()
    today = date.today()
    results = []
    for registered, product, warranty in rows:
        warranty_data = None
        if warranty:
            end = date.fromisoformat(warranty.end_date)
            rem = (end - today).days
            if rem < 0:
                stat = "Expired"
            elif rem <= 30:
                stat = "Approaching Expiry"
            else:
                stat = "Active"
            warranty_data = {
                "id": warranty.id,
                "warranty_code": f"WAR-{warranty.id:05d}",
                "start_date": warranty.start_date,
                "end_date": warranty.end_date,
                "remaining_days": rem,
                "status": stat,
                "warranty_provider": warranty.warranty_provider or "AssureX Official Care",
                "warranty_type": warranty.warranty_type or "Standard",
                "coverage_conditions": warranty.coverage_conditions or "Covers manufacturing defects, internal component failures, and electrical faults under normal operating conditions.",
                "exclusions": warranty.exclusions or "Damage caused by accidents, liquid intrusion, unauthorized disassembly, or physical abuse.",
                "service_center_details": warranty.service_center_details or "AssureX Central Authorized Center, 123 Tech Park Blvd (Hotline: 1800-ASSUREX)",
                "is_active": warranty.is_active,
            }
        results.append({
            "id": registered.id,
            "registration_code": f"REG-{registered.id:05d}",
            "product_id": product.id,
            "product_code": f"PRD-{product.id:04d}",
            "name": product.name,
            "category": product.category,
            "brand": product.brand,
            "model": product.model,
            "warranty_months": product.warranty_months,
            "serial_number": registered.serial_number,
            "purchase_date": registered.purchase_date,
            "purchase_price": registered.purchase_price,
            "retailer": registered.retailer or "Authorized Dealer",
            "is_active": registered.is_active,
            "warranty": warranty_data,
        })
    return results


@router.post("/api/products/register", status_code=201)
def register_product(
    payload: ProductRegister,
    account: CustomerAccount = Depends(require_roles("CUSTOMER")),
    db: Session = Depends(get_db),
):
    product = db.get(Product, payload.product_id)
    if product is None or not product.is_active:
        raise HTTPException(status_code=404, detail="Active product not found.")

    registered = RegisteredProduct(
        account_id=account.id,
        product_id=product.id,
        serial_number=payload.serial_number.strip(),
        purchase_date=payload.purchase_date.isoformat(),
        purchase_price=payload.purchase_price,
        retailer=payload.retailer.strip() if payload.retailer else None,
    )
    db.add(registered)
    try:
        db.flush()
        expiry = add_months(payload.purchase_date, product.warranty_months)
        rem = (expiry - date.today()).days
        if rem < 0:
            stat = "Expired"
        elif rem <= 30:
            stat = "Approaching Expiry"
        else:
            stat = "Active"

        warranty = Warranty(
            registered_product_id=registered.id,
            start_date=payload.purchase_date.isoformat(),
            end_date=expiry.isoformat(),
            status=stat,
            warranty_provider="AssureX Official Care",
            warranty_type="Standard",
            coverage_conditions="Covers manufacturing defects, internal component failures, and electrical faults under normal operating conditions.",
            exclusions="Damage caused by accidents, liquid intrusion, unauthorized disassembly, or physical abuse.",
            service_center_details="AssureX Central Authorized Center, 123 Tech Park Blvd (Hotline: 1800-ASSUREX)",
            is_active=True,
        )
        db.add(warranty)
        record_audit(
            db,
            account=account,
            action="PRODUCT_REGISTERED",
            resource_type="PRODUCT",
            resource_id=str(registered.id),
            details={
                "serial_number": registered.serial_number,
                "purchase_price": registered.purchase_price,
                "retailer": registered.retailer,
            },
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Serial number is already registered.") from exc

    return {
        "id": registered.id,
        "registration_code": f"REG-{registered.id:05d}",
        "product_id": product.id,
        "product_code": f"PRD-{product.id:04d}",
        "name": product.name,
        "brand": product.brand,
        "model": product.model,
        "serial_number": registered.serial_number,
        "purchase_date": registered.purchase_date,
        "purchase_price": registered.purchase_price,
        "retailer": registered.retailer or "Authorized Dealer",
        "warranty": {
            "id": warranty.id,
            "warranty_code": f"WAR-{warranty.id:05d}",
            "start_date": payload.purchase_date.isoformat(),
            "end_date": expiry.isoformat(),
            "remaining_days": rem,
            "status": stat,
            "warranty_provider": warranty.warranty_provider,
            "warranty_type": warranty.warranty_type,
            "coverage_conditions": warranty.coverage_conditions,
            "exclusions": warranty.exclusions,
            "service_center_details": warranty.service_center_details,
            "is_active": warranty.is_active,
        },
    }


@router.get("/api/warranties")
def list_warranties(
    account: CustomerAccount = Depends(
        require_roles("CUSTOMER", "SERVICE_CENTER", "REVIEWER", "ADMIN")
    ),
    db: Session = Depends(get_db),
):
    statement = (
        select(Warranty, RegisteredProduct, Product, CustomerAccount)
        .join(RegisteredProduct, RegisteredProduct.id == Warranty.registered_product_id)
        .join(Product, Product.id == RegisteredProduct.product_id)
        .join(CustomerAccount, CustomerAccount.id == RegisteredProduct.account_id)
    )
    if account.role == "CUSTOMER":
        statement = statement.where(RegisteredProduct.account_id == account.id)

    rows = db.execute(statement.order_by(Warranty.end_date.asc())).all()
    today = date.today()
    results = []
    for warranty, registered, product, owner in rows:
        end = date.fromisoformat(warranty.end_date)
        rem = (end - today).days
        if rem < 0:
            stat = "Expired"
        elif rem <= 30:
            stat = "Approaching Expiry"
        else:
            stat = "Active"

        results.append({
            "id": warranty.id,
            "warranty_code": f"WAR-{warranty.id:05d}",
            "customer_email": owner.email,
            "customer_name": getattr(owner, "full_name", None) or owner.username or owner.email.split("@")[0],
            "product": product.name,
            "product_code": f"PRD-{product.id:04d}",
            "category": product.category,
            "brand": product.brand,
            "model": product.model,
            "serial_number": registered.serial_number,
            "purchase_date": registered.purchase_date,
            "purchase_price": registered.purchase_price,
            "retailer": registered.retailer or "Authorized Dealer",
            "start_date": warranty.start_date,
            "end_date": warranty.end_date,
            "remaining_days": rem,
            "status": stat,
            "warranty_provider": warranty.warranty_provider or "AssureX Official Care",
            "warranty_type": warranty.warranty_type or "Standard",
            "coverage_conditions": warranty.coverage_conditions or "Covers manufacturing defects, internal component failures, and electrical faults under normal operating conditions.",
            "exclusions": warranty.exclusions or "Damage caused by accidents, liquid intrusion, unauthorized disassembly, or physical abuse.",
            "service_center_details": warranty.service_center_details or "AssureX Central Authorized Center, 123 Tech Park Blvd (Hotline: 1800-ASSUREX)",
            "is_active": warranty.is_active,
        })
    return results


@router.patch("/api/warranties/{warranty_id}/active")
def set_warranty_active(
    warranty_id: int,
    payload: ActiveChange,
    account: CustomerAccount = Depends(require_roles("ADMIN", "SERVICE_CENTER")),
    db: Session = Depends(get_db),
):
    warranty = db.get(Warranty, warranty_id)
    if warranty is None:
        raise HTTPException(status_code=404, detail="Warranty not found.")
    warranty.is_active = payload.is_active
    record_audit(
        db,
        account=account,
        action="WARRANTY_STATUS_CHANGED",
        resource_type="WARRANTY",
        resource_id=str(warranty.id),
        details={"is_active": warranty.is_active, "status": warranty.status},
    )
    db.commit()
    return {"id": warranty.id, "is_active": warranty.is_active}
