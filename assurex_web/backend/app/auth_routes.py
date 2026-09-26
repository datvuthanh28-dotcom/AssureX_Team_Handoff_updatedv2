from datetime import datetime, timedelta
import hashlib
import hmac
import os
import re
import secrets
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog, CustomerAccount, CustomerSession


router = APIRouter(prefix="/api/auth", tags=["Customer Authentication"])
bearer_scheme = HTTPBearer(auto_error=False)
PASSWORD_ITERATIONS = 310_000
SESSION_DAYS = 30
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=150)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not EMAIL_PATTERN.fullmatch(normalized):
            raise ValueError("Enter a valid email address.")
        return normalized


class AdminCredentials(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=128)


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: str = Field(min_length=3, max_length=150)
    password: str = Field(min_length=8, max_length=128)
    role: Literal["CUSTOMER", "SERVICE_CENTER", "REVIEWER", "ADMIN"]

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not EMAIL_PATTERN.fullmatch(normalized):
            raise ValueError("Enter a valid email address.")
        return normalized


class ActiveUpdate(BaseModel):
    is_active: bool


def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        PASSWORD_ITERATIONS,
    ).hex()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def record_audit(
    db: Session,
    *,
    account: CustomerAccount | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    result: str = "SUCCESS",
    details: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=account.id if account else None,
            actor_email=account.email if account else "system",
            actor_role=account.role if account else "SYSTEM",
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            result=result,
            details=details or {},
        )
    )


def issue_session(db: Session, account: CustomerAccount) -> dict:
    token = secrets.token_urlsafe(32)
    db.add(
        CustomerSession(
            account_id=account.id,
            token_hash=hash_token(token),
            expires_at=datetime.utcnow() + timedelta(days=SESSION_DAYS),
        )
    )
    record_audit(
        db,
        account=account,
        action="LOGIN",
        resource_type="ACCOUNT",
        resource_id=str(account.id),
    )
    db.commit()
    return {
        "access_token": token,
        "token_type": "bearer",
        "email": account.email,
        "role": account.role,
    }


def get_current_customer(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> CustomerAccount:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Sign in is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    customer_session = db.scalar(
        select(CustomerSession).where(
            CustomerSession.token_hash == hash_token(credentials.credentials),
            CustomerSession.expires_at > datetime.utcnow(),
        )
    )
    if customer_session is None:
        raise HTTPException(
            status_code=401,
            detail="Session is invalid or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    account = db.get(CustomerAccount, customer_session.account_id)
    if account is None:
        raise HTTPException(status_code=401, detail="Account no longer exists.")
    if not account.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive.")
    return account


def require_roles(*roles: str):
    def check_role(
        account: CustomerAccount = Depends(get_current_customer),
    ) -> CustomerAccount:
        if account.role not in roles:
            raise HTTPException(
                status_code=403,
                detail="Your role cannot access this resource.",
            )
        return account

    return check_role


def seed_default_admin(db: Session) -> None:
    admin = db.scalar(
        select(CustomerAccount).where(
            CustomerAccount.username == "admin"
        )
    )
    if admin is not None:
        return

    salt = secrets.token_hex(16)
    admin = CustomerAccount(
        username="admin",
        email="admin@assurex.local",
        role="ADMIN",
        is_active=True,
        password_salt=salt,
        password_hash=hash_password(
            os.getenv("ASSUREX_ADMIN_PASSWORD", "123"),
            salt,
        ),
    )
    db.add(admin)
    db.flush()
    record_audit(
        db,
        account=admin,
        action="ACCOUNT_CREATED",
        resource_type="ACCOUNT",
        resource_id=str(admin.id),
        details={"source": "bootstrap"},
    )
    db.commit()


@router.post("/register", status_code=201)
def register(payload: Credentials, db: Session = Depends(get_db)):
    existing = db.scalar(
        select(CustomerAccount).where(CustomerAccount.email == payload.email)
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="An account already exists for this email.")

    salt = secrets.token_hex(16)
    account = CustomerAccount(
        email=payload.email,
        role="CUSTOMER",
        is_active=True,
        password_salt=salt,
        password_hash=hash_password(payload.password, salt),
    )
    db.add(account)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="An account already exists for this email.",
        ) from exc

    db.refresh(account)
    record_audit(
        db,
        account=account,
        action="ACCOUNT_CREATED",
        resource_type="ACCOUNT",
        resource_id=str(account.id),
    )
    return issue_session(db, account)


@router.post("/login")
def login(payload: Credentials, db: Session = Depends(get_db)):
    account = db.scalar(
        select(CustomerAccount).where(CustomerAccount.email == payload.email)
    )
    candidate_hash = (
        hash_password(payload.password, account.password_salt)
        if account is not None
        else hash_password(payload.password, "00" * 16)
    )
    if account is None or not hmac.compare_digest(
        candidate_hash,
        account.password_hash,
    ):
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    if account.role != "CUSTOMER" or not account.is_active:
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")

    return issue_session(db, account)


@router.post("/workspace/login")
@router.post("/admin/login")
def admin_login(
    payload: AdminCredentials,
    db: Session = Depends(get_db),
):
    admin = db.scalar(
        select(CustomerAccount).where(
            CustomerAccount.username == payload.username.strip(),
            CustomerAccount.role.in_(("ADMIN", "REVIEWER", "SERVICE_CENTER")),
            CustomerAccount.is_active.is_(True),
        )
    )
    candidate_hash = (
        hash_password(payload.password, admin.password_salt)
        if admin is not None
        else hash_password(payload.password, "00" * 16)
    )
    if admin is None or not hmac.compare_digest(
        candidate_hash,
        admin.password_hash,
    ):
        raise HTTPException(status_code=401, detail="Username or password is incorrect.")
    return issue_session(db, admin)


@router.get("/me")
def current_customer(account: CustomerAccount = Depends(get_current_customer)):
    return {
        "id": account.id,
        "username": account.username,
        "email": account.email,
        "role": account.role,
    }


@router.post("/logout")
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    if credentials is not None:
        customer_session = db.scalar(
            select(CustomerSession).where(
                CustomerSession.token_hash == hash_token(credentials.credentials)
            )
        )
        if customer_session is not None:
            account = db.get(CustomerAccount, customer_session.account_id)
            db.delete(customer_session)
            record_audit(
                db,
                account=account,
                action="LOGOUT",
                resource_type="ACCOUNT",
                resource_id=str(account.id) if account else None,
            )
            db.commit()
    return {"ok": True}


@router.get("/users")
def list_users(
    _: CustomerAccount = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    users = db.scalars(
        select(CustomerAccount).order_by(CustomerAccount.created_at.desc())
    ).all()
    return [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at,
        }
        for user in users
    ]


@router.post("/users", status_code=201)
def create_user(
    payload: UserCreate,
    admin: CustomerAccount = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    existing = db.scalar(
        select(CustomerAccount).where(
            or_(
                CustomerAccount.email == payload.email,
                CustomerAccount.username == payload.username.strip(),
            )
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email or username is already in use.")

    salt = secrets.token_hex(16)
    user = CustomerAccount(
        username=payload.username.strip(),
        email=payload.email,
        role=payload.role,
        is_active=True,
        password_salt=salt,
        password_hash=hash_password(payload.password, salt),
    )
    db.add(user)
    try:
        db.flush()
        record_audit(
            db,
            account=admin,
            action="ACCOUNT_CREATED",
            resource_type="ACCOUNT",
            resource_id=str(user.id),
            details={"email": user.email, "role": user.role},
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email or username is already in use.") from exc
    db.refresh(user)
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at,
    }


@router.patch("/users/{user_id}/active")
def set_user_active(
    user_id: int,
    payload: ActiveUpdate,
    admin: CustomerAccount = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    user = db.get(CustomerAccount, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.id == admin.id and not payload.is_active:
        raise HTTPException(status_code=400, detail="The active admin cannot deactivate itself.")

    user.is_active = payload.is_active
    if not user.is_active:
        db.query(CustomerSession).filter(
            CustomerSession.account_id == user.id
        ).delete(synchronize_session=False)
    record_audit(
        db,
        account=admin,
        action="ACCOUNT_STATUS_CHANGED",
        resource_type="ACCOUNT",
        resource_id=str(user.id),
        details={"is_active": user.is_active},
    )
    db.commit()
    return {"id": user.id, "is_active": user.is_active}


