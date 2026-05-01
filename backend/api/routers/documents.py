import os
import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from db.session import get_db
from models.models import Document, Shipment, CustomsRecord
from schemas.schemas import DocumentOut
from core.security import get_current_user_id
from core.config import settings

router = APIRouter(prefix="/api/shipments", tags=["documents"])

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/app/data/uploads")
MAX_SIZE_MB = int(os.environ.get("MAX_UPLOAD_SIZE_MB", "20"))
ALLOWED_TYPES = {
    "application/pdf",
    "image/jpeg", "image/png", "image/webp",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain", "text/csv",
}

DOC_TYPE_CHOICES = [
    "Commercial Invoice",
    "Bill of Lading",
    "Packing List",
    "Certificate of Origin",
    "Phytosanitary Certificate",
    "Pesticide Residue Report",
    "Customs Declaration",
    "Insurance Certificate",
    "Quality Certificate",
    "Contract",
    "Other",
]


def _ensure_upload_dir(shipment_id: int) -> str:
    path = os.path.join(UPLOAD_DIR, str(shipment_id))
    os.makedirs(path, exist_ok=True)
    return path


@router.get("/{shipment_id}/documents", response_model=List[DocumentOut])
def list_documents(
    shipment_id: int,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    if not db.query(Shipment).filter(Shipment.id == shipment_id).first():
        raise HTTPException(404, "Shipment not found")
    docs = db.query(Document).filter(Document.shipment_id == shipment_id).all()
    return [DocumentOut.model_validate(d) for d in docs]


@router.post("/{shipment_id}/documents", response_model=DocumentOut, status_code=201)
async def upload_document(
    shipment_id: int,
    doc_type: str = Form(...),
    customs_record_id: int = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    # Validate shipment exists
    if not db.query(Shipment).filter(Shipment.id == shipment_id).first():
        raise HTTPException(404, "Shipment not found")

    # Validate customs record if provided
    if customs_record_id:
        cr = db.query(CustomsRecord).filter(
            CustomsRecord.id == customs_record_id,
            CustomsRecord.shipment_id == shipment_id,
        ).first()
        if not cr:
            raise HTTPException(404, "Customs record not found for this shipment")

    # Validate doc_type
    if doc_type not in DOC_TYPE_CHOICES:
        raise HTTPException(400, f"Invalid doc_type. Choose from: {DOC_TYPE_CHOICES}")

    # Validate file type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"File type '{file.content_type}' not allowed")

    # Read and check size
    content = await file.read()
    if len(content) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {MAX_SIZE_MB}MB limit")

    # Build unique filename and save
    ext = os.path.splitext(file.filename or "file")[1] or ".bin"
    unique_name = f"{uuid.uuid4().hex}{ext}"
    save_dir = _ensure_upload_dir(shipment_id)
    save_path = os.path.join(save_dir, unique_name)

    with open(save_path, "wb") as f:
        f.write(content)

    # Persist record
    doc = Document(
        shipment_id=shipment_id,
        customs_record_id=customs_record_id,
        doc_type=doc_type,
        filename=file.filename or unique_name,
        file_path=save_path,
        uploaded_by=user_id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return DocumentOut.model_validate(doc)


@router.get("/{shipment_id}/documents/{doc_id}/download")
def download_document(
    shipment_id: int,
    doc_id: int,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.shipment_id == shipment_id,
    ).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    if not os.path.exists(doc.file_path):
        raise HTTPException(410, "File no longer available on server")
    return FileResponse(
        path=doc.file_path,
        filename=doc.filename,
        media_type="application/octet-stream",
    )


@router.delete("/{shipment_id}/documents/{doc_id}", status_code=204)
def delete_document(
    shipment_id: int,
    doc_id: int,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.shipment_id == shipment_id,
    ).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    # Remove file from disk
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    db.delete(doc)
    db.commit()
