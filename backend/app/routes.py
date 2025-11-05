import uuid
from pathlib import Path
from typing import Dict, Optional

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi import BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .ocr import run_ocr_pipeline
from .db import get_db
from .models import Upload, Extraction

router = APIRouter(prefix="/api", tags=["api"])

UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class ExtractionResult(BaseModel):
    extraction_id: str
    raw_text: Optional[str] = None
    data: Optional[Dict] = None
    status: str


class VerifyRequest(BaseModel):
    data: Dict


class SubmitRequest(BaseModel):
    extraction_id: str
    data: Dict


_STORE: Dict[str, ExtractionResult] = {}


@router.post("/upload", response_model=ExtractionResult)
async def upload_document(background: BackgroundTasks, file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(400, "Missing filename")

    ext_id = str(uuid.uuid4())
    save_path = UPLOAD_DIR / f"{ext_id}_{file.filename}"
    content = await file.read()
    save_path.write_bytes(content)

    result = ExtractionResult(extraction_id=ext_id, status="processing")
    _STORE[ext_id] = result

    # Persist upload and extraction
    upload_row = Upload(extraction_id=ext_id, file_path=str(save_path))
    db.add(upload_row)
    db.flush()
    extraction_row = Extraction(upload_id=upload_row.id, status="processing")
    db.add(extraction_row)
    db.commit()

    background.add_task(_process_ocr, ext_id, save_path)
    return result


def _process_ocr(extraction_id: str, file_path: Path):
    try:
        raw_text, parsed = run_ocr_pipeline(file_path)
        _STORE[extraction_id] = ExtractionResult(
            extraction_id=extraction_id,
            raw_text=raw_text,
            data=parsed,
            status="completed",
        )

        # Update DB in a new session
        from .db import SessionLocal
        with SessionLocal() as db:
            upload_row = db.query(Upload).filter(Upload.extraction_id == extraction_id).first()
            if upload_row and upload_row.extraction:
                upload_row.extraction.status = "completed"
                upload_row.extraction.raw_text = raw_text
                upload_row.extraction.extracted_json = parsed
                db.commit()
    except Exception as exc:
        _STORE[extraction_id] = ExtractionResult(
            extraction_id=extraction_id,
            raw_text=None,
            data=None,
            status=f"error: {exc}",
        )

        from .db import SessionLocal
        with SessionLocal() as db:
            upload_row = db.query(Upload).filter(Upload.extraction_id == extraction_id).first()
            if upload_row and upload_row.extraction:
                upload_row.extraction.status = "error"
                db.commit()


@router.get("/result/{extraction_id}", response_model=ExtractionResult)
def get_result(extraction_id: str, db: Session = Depends(get_db)):
    if extraction_id not in _STORE:
        # Try DB fallback
        upload_row = db.query(Upload).filter(Upload.extraction_id == extraction_id).first()
        if not upload_row or not upload_row.extraction:
            raise HTTPException(404, "Unknown extraction id")
        res = ExtractionResult(
            extraction_id=extraction_id,
            raw_text=upload_row.extraction.raw_text,
            data=upload_row.extraction.extracted_json,
            status=upload_row.extraction.status,
        )
        _STORE[extraction_id] = res
    return _STORE[extraction_id]


@router.post("/verify", response_model=Dict)
def verify(request: VerifyRequest):
    data = request.data
    # Minimal validation rules; extend later with LLM/rules
    errors = {}
    # Example: ensure expiry > today if present
    try:
        from datetime import date
        if "expiry_date" in data:
            y, m, d = map(int, data["expiry_date"].split("-"))
            if date(y, m, d) <= date.today():
                errors["expiry_date"] = "Expiry must be in the future"
    except Exception:
        errors["expiry_date"] = "Invalid date format (YYYY-MM-DD)"

    # Passport format example: P + 7 alphanumerics
    import re
    if "passport_number" in data:
        if not re.fullmatch(r"P[A-Z0-9]{7}", str(data["passport_number"]).upper()):
            errors["passport_number"] = "Invalid passport format (P[A-Z0-9]{7})"

    return {"valid": len(errors) == 0, "errors": errors, "data": data}


@router.post("/submit", response_model=Dict)
def submit(request: SubmitRequest, db: Session = Depends(get_db)):
    # Update memory store
    _STORE[request.extraction_id] = ExtractionResult(
        extraction_id=request.extraction_id,
        raw_text=_STORE.get(request.extraction_id, ExtractionResult(extraction_id=request.extraction_id, status="unknown")).raw_text,
        data=request.data,
        status="submitted",
    )
    # Persist verified_json and status
    upload_row = db.query(Upload).filter(Upload.extraction_id == request.extraction_id).first()
    if upload_row and upload_row.extraction:
        upload_row.extraction.verified_json = request.data
        upload_row.extraction.status = "submitted"
        db.commit()
    return {"status": "submitted", "extraction_id": request.extraction_id}


