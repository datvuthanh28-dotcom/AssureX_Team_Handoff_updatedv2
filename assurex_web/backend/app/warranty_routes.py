from pathlib import Path
import hashlib
import uuid
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.auth_routes import record_audit, require_roles
from app.database import get_db
from app.models import CustomerAccount
from app.ocr.ocr_service import (
    extract_warranty_image,
)
router = APIRouter(
    prefix="/api/customer",
    tags=["Customer Warranty & Evidence"],
)
WARRANTY_UPLOAD_DIR = Path(
    "app/uploads/warranty_cards"
)
WARRANTY_UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)
EVIDENCE_UPLOAD_DIR = Path(
    "app/uploads/evidence"
)
EVIDENCE_UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
EVIDENCE_ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "application/pdf": ".pdf",
    "video/mp4": ".mp4",
}
MAX_FILE_SIZE = 8 * 1024 * 1024
MAX_EVIDENCE_SIZE = 25 * 1024 * 1024
@router.post("/warranty/extract")


async def extract_warranty_card(
    file: UploadFile = File(...),
    account: CustomerAccount = Depends(require_roles("CUSTOMER")),
    db: Session = Depends(get_db),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG and WEBP images are supported.",
        )
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty.",
        )
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Maximum file size is 8 MB.",
        )
    sha256 = hashlib.sha256(content).hexdigest()
    document_id = "WAR-" + uuid.uuid4().hex[:12].upper()
    extension = ALLOWED_IMAGE_TYPES[file.content_type]
    path = WARRANTY_UPLOAD_DIR / f"{document_id}{extension}"
    path.write_bytes(content)
    try:
        result = extract_warranty_image(path)
    except Exception as exc:
        path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail=f"OCR failed: {exc}",
        ) from exc
    extracted = result["extracted_data"]
    extracted_count = sum(
        value not in (None, "") for value in extracted.values()
    )
    record_audit(
        db,
        account=account,
        action="DOCUMENT_UPLOADED",
        resource_type="DOCUMENT",
        resource_id=document_id,
        details={
            "document_type": "WARRANTY_CARD",
            "filename": file.filename,
            "sha256": sha256,
        },
    )
    db.commit()
    return {
        "document_id": document_id,
        "filename": file.filename,
        "sha256": sha256,
        "file_url": f"/api/customer/evidence/file/{document_id}{extension}",
        "ocr_confidence": result["ocr_confidence"],
        "extracted_fields": extracted_count,
        "extracted_data": extracted,
        "text_preview": result["raw_text"][:500],
    }
@router.post("/evidence/upload")


async def upload_evidence_file(
    file: UploadFile = File(...),
    document_type: str = Form("evidence"),
    account: CustomerAccount = Depends(
        require_roles("CUSTOMER", "SERVICE_CENTER", "REVIEWER", "ADMIN")
    ),
    db: Session = Depends(get_db),
):
    content_type = file.content_type or "application/octet-stream"
    if content_type not in EVIDENCE_ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{content_type}'. Supported: JPG, PNG, WEBP, PDF, MP4.",
        )
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > MAX_EVIDENCE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Maximum evidence file size is 25 MB.",
        )
    sha256 = hashlib.sha256(content).hexdigest()
    doc_id = "EVD-" + uuid.uuid4().hex[:12].upper()
    ext = EVIDENCE_ALLOWED_TYPES[content_type]
    file_name = f"{doc_id}{ext}"
    path = EVIDENCE_UPLOAD_DIR / file_name
    path.write_bytes(content)
    record_audit(
        db,
        account=account,
        action="DOCUMENT_UPLOADED",
        resource_type="DOCUMENT",
        resource_id=doc_id,
        details={
            "document_type": document_type,
            "filename": file.filename,
            "sha256": sha256,
            "size_bytes": len(content),
        },
    )
    db.commit()
    return {
        "document_id": doc_id,
        "filename": file.filename,
        "sha256": sha256,
        "file_url": f"/api/customer/evidence/file/{file_name}",
        "file_size": len(content),
        "content_type": content_type,
    }
@router.get("/evidence/file/{file_name}")


def get_evidence_file(file_name: str):
    safe_name = Path(file_name).name
    if not safe_name or ".." in safe_name:
        raise HTTPException(status_code=400, detail="Invalid file name.")
    path = EVIDENCE_UPLOAD_DIR / safe_name
    if not path.exists():
        path = WARRANTY_UPLOAD_DIR / safe_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(path)
