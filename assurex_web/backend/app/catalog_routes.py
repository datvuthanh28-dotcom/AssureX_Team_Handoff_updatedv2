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
    return [
        {
            "id": registered.id,
            "product_id": product.id,
            "name": product.name,
            "category": product.category,
            "brand": product.brand,
            "model": product.model,
            "warranty_months": product.warranty_months,
            "serial_number": registered.serial_number,
            "purchase_date": registered.purchase_date,
            "is_active": registered.is_active,
            "warranty": (
                {
                    "id": warranty.id,
                    "start_date": warranty.start_date,
                    "end_date": warranty.end_date,
                    "status": (
                        "Active"
                        if date.fromisoformat(warranty.end_date) >= date.today()
                        else "Expired"
                    ),
                    "is_active": warranty.is_active,
                }
                if warranty
                else None
            ),
        }
        for registered, product, warranty in rows
    ]


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
    )
    db.add(registered)
    try:
        db.flush()
        expiry = add_months(payload.purchase_date, product.warranty_months)
        warranty = Warranty(
            registered_product_id=registered.id,
            start_date=payload.purchase_date.isoformat(),
            end_date=expiry.isoformat(),
            status="Active" if expiry >= date.today() else "Expired",
            is_active=True,
        )
        db.add(warranty)
        record_audit(
            db,
            account=account,
            action="PRODUCT_REGISTERED",
            resource_type="PRODUCT",
            resource_id=str(registered.id),
            details={"serial_number": registered.serial_number},
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Serial number is already registered.") from exc

    return {
        "id": registered.id,
        "product_id": product.id,
        "name": product.name,
        "brand": product.brand,
        "model": product.model,
        "serial_number": registered.serial_number,
        "purchase_date": registered.purchase_date,
        "warranty": {
            "start_date": payload.purchase_date.isoformat(),
            "end_date": expiry.isoformat(),
            "status": (
                "Active"
                if date.fromisoformat(warranty.end_date) >= date.today()
                else "Expired"
            ),
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
    return [
        {
            "id": warranty.id,
            "customer_email": owner.email,
            "product": product.name,
            "category": product.category,
            "brand": product.brand,
            "model": product.model,
            "serial_number": registered.serial_number,
            "start_date": warranty.start_date,
            "end_date": warranty.end_date,
            "status": warranty.status,
            "is_active": warranty.is_active,
        }
        for warranty, registered, product, owner in rows
    ]


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