from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth_routes import get_current_customer
from app.database import get_db
from app.models import CustomerAccount, Notification


router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


def add_notification(
    db: Session,
    *,
    account_id: int,
    title: str,
    message: str,
    resource_type: str,
    resource_id: str,
) -> None:
    db.add(
        Notification(
            account_id=account_id,
            title=title,
            message=message,
            resource_type=resource_type,
            resource_id=resource_id,
        )
    )


@router.get("")
def list_notifications(
    account: CustomerAccount = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    items = db.scalars(
        select(Notification)
        .where(Notification.account_id == account.id)
        .order_by(Notification.created_at.desc())
    ).all()
    return [
        {
            "id": item.id,
            "title": item.title,
            "message": item.message,
            "resource_type": item.resource_type,
            "resource_id": item.resource_id,
            "is_read": item.is_read,
            "created_at": item.created_at,
        }
        for item in items
    ]


@router.post("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    account: CustomerAccount = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    item = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.account_id == account.id,
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Notification not found.")
    item.is_read = True
    db.commit()
    return {"id": item.id, "is_read": item.is_read}