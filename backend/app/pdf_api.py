from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import PdfGeneration, PdfSavedValue, PdfTemplate
from .services.pdf_forms import (
    PdfStorage, analyze_pdf, decrypt_value, encrypt_value, field_key, fill_pdf,
    new_storage_key, safe_filename,
)


class PdfFieldLayout(BaseModel):
    key: str = Field(min_length=1, max_length=120)
    pdf_name: str = Field(default="", max_length=200)
    label: str = Field(min_length=1, max_length=200)
    type: str = Field(default="text", pattern="^(text|email|date|checkbox|select)$")
    page: int = Field(default=0, ge=0)
    left: float = Field(default=0.35, ge=0, le=1)
    top: float = Field(default=0.1, ge=0, le=1)
    width: float = Field(default=0.5, gt=0, le=1)
    height: float = Field(default=0.025, gt=0, le=0.25)
    required: bool = False
    source: str = Field(default="manual", pattern="^(acroform|text|ocr|manual)$")


class PdfFieldLayoutInput(BaseModel):
    fields: list[PdfFieldLayout] = Field(max_length=200)


class PdfGenerateInput(BaseModel):
    values: dict[str, str | bool] = Field(default_factory=dict)
    remember_keys: list[str] = Field(default_factory=list, max_length=200)


def _owned_template(db: Session, template_id: int) -> PdfTemplate:
    item = db.scalar(select(PdfTemplate).where(PdfTemplate.id == template_id))
    if not item:
        raise HTTPException(status_code=404, detail="PDF template not found")
    return item


def _saved_suggestions(db: Session, fields: list[dict[str, Any]]) -> dict[str, str]:
    keys = {field.get("key", "") for field in fields}
    if not keys:
        return {}
    result: dict[str, str] = {}
    for saved in db.scalars(select(PdfSavedValue).where(PdfSavedValue.field_key.in_(keys))).all():
        try:
            result[saved.field_key] = decrypt_value(saved.encrypted_value)
        except Exception:
            continue
    return result


def _serialize_template(item: PdfTemplate, db: Session, detailed: bool = False) -> dict[str, Any]:
    fields = json.loads(item.fields_json or "[]")
    analysis = json.loads(item.analysis_json or "{}")
    data = {
        "id": item.id,
        "name": item.name,
        "original_filename": item.original_filename,
        "page_count": item.page_count,
        "analysis_mode": item.analysis_mode,
        "field_count": len(fields),
        "is_signed": item.is_signed,
        "warnings": analysis.get("warnings", []),
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }
    if detailed:
        data.update({
            "fields": fields,
            "page_sizes": analysis.get("page_sizes", []),
            "suggestions": _saved_suggestions(db, fields),
            "original_url": f"/api/pdf-forms/{item.id}/original",
        })
    return data


def create_pdf_router(get_db: Callable) -> APIRouter:
    router = APIRouter(prefix="/api/pdf-forms", tags=["PDF forms"])

    @router.get("/status")
    def pdf_status(db: Session = Depends(get_db)):
        return {
            "status": "ready",
            "storage": "azure" if settings.azure_storage_connection_string else "private_local",
            "ocr": "local",
            "templates": len(list(db.scalars(select(PdfTemplate.id)).all())),
        }

    @router.get("")
    def list_templates(db: Session = Depends(get_db)):
        items = db.scalars(select(PdfTemplate).order_by(PdfTemplate.updated_at.desc())).all()
        return [_serialize_template(item, db) for item in items]

    @router.post("/upload", status_code=201)
    async def upload_pdf(
        file: UploadFile = File(...),
        name: str = Form(default=""),
        db: Session = Depends(get_db),
    ):
        filename = safe_filename(file.filename or "document.pdf")
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Upload a PDF file")
        limit = settings.pdf_max_upload_mb * 1024 * 1024
        data = await file.read(limit + 1)
        if len(data) > limit:
            raise HTTPException(status_code=413, detail=f"PDF must be {settings.pdf_max_upload_mb} MB or smaller")
        if not data.startswith(b"%PDF-"):
            raise HTTPException(status_code=400, detail="The uploaded file is not a valid PDF")
        digest = hashlib.sha256(data).hexdigest()
        existing = db.scalar(select(PdfTemplate).where(PdfTemplate.sha256 == digest))
        if existing:
            return {"reused": True, "template": _serialize_template(existing, db, detailed=True)}
        try:
            analysis = analyze_pdf(data)
        except Exception as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        user_id = int(db.info["user_id"])
        storage_key = new_storage_key(user_id, "templates", filename)
        storage = PdfStorage()
        storage.put(storage_key, data)
        item = PdfTemplate(
            name=(name.strip() or Path(filename).stem)[:160],
            original_filename=filename,
            storage_key=storage_key,
            sha256=digest,
            page_count=analysis["page_count"],
            analysis_mode=analysis["mode"],
            fields_json=json.dumps(analysis["fields"], separators=(",", ":")),
            analysis_json=json.dumps({"page_sizes": analysis["page_sizes"], "warnings": analysis["warnings"]}, separators=(",", ":")),
            is_signed=analysis["signed"],
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return {"reused": False, "template": _serialize_template(item, db, detailed=True)}

    @router.get("/{template_id}")
    def get_template(template_id: int, db: Session = Depends(get_db)):
        return _serialize_template(_owned_template(db, template_id), db, detailed=True)

    @router.put("/{template_id}/fields")
    def update_fields(template_id: int, payload: PdfFieldLayoutInput, db: Session = Depends(get_db)):
        item = _owned_template(db, template_id)
        fields = [field.model_dump() for field in payload.fields]
        if len({field["key"] for field in fields}) != len(fields):
            raise HTTPException(status_code=400, detail="Field keys must be unique")
        if any(field["page"] >= item.page_count for field in fields):
            raise HTTPException(status_code=400, detail="A field points outside the PDF page range")
        item.fields_json = json.dumps(fields, separators=(",", ":"))
        db.commit()
        db.refresh(item)
        return _serialize_template(item, db, detailed=True)

    @router.get("/{template_id}/original")
    def original_pdf(template_id: int, db: Session = Depends(get_db)):
        item = _owned_template(db, template_id)
        data = PdfStorage().get(item.storage_key)
        return Response(data, media_type="application/pdf", headers={
            "Content-Disposition": f'inline; filename="{safe_filename(item.original_filename)}"',
            "Cache-Control": "private, no-store",
        })

    @router.post("/{template_id}/generate", status_code=201)
    def generate_pdf(template_id: int, payload: PdfGenerateInput, db: Session = Depends(get_db)):
        item = _owned_template(db, template_id)
        if item.is_signed:
            raise HTTPException(status_code=409, detail="This PDF is digitally signed; filling it would invalidate the signature")
        fields = json.loads(item.fields_json or "[]")
        known = {field["key"]: field for field in fields}
        values = {key: value for key, value in payload.values.items() if key in known}
        missing = [field["label"] for field in fields if field.get("required") and not str(values.get(field["key"], "")).strip()]
        if missing:
            raise HTTPException(status_code=400, detail=f"Complete required fields: {', '.join(missing)}")
        try:
            original = PdfStorage().get(item.storage_key)
            generated = fill_pdf(original, fields, values)
        except Exception as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        output_name = safe_filename(f"{Path(item.original_filename).stem}-filled-{timestamp}.pdf")
        storage_key = new_storage_key(int(db.info["user_id"]), "generated", output_name)
        PdfStorage().put(storage_key, generated)
        generation = PdfGeneration(template_id=item.id, output_filename=output_name, storage_key=storage_key,
                                   values_json=json.dumps({"fields": sorted(values)}, separators=(",", ":")))
        db.add(generation)
        for key in set(payload.remember_keys) & set(values):
            saved = db.scalar(select(PdfSavedValue).where(PdfSavedValue.field_key == key))
            if not saved:
                saved = PdfSavedValue(field_key=key, label=known[key]["label"], encrypted_value="")
                db.add(saved)
            saved.label = known[key]["label"]
            saved.encrypted_value = encrypt_value(str(values[key]))
        db.commit()
        db.refresh(generation)
        return {
            "generation_id": generation.id,
            "filename": generation.output_filename,
            "download_url": f"/api/pdf-forms/generations/{generation.id}/download",
            "quality": {"page_count": item.page_count, "original_preserved": True},
        }

    @router.get("/generations/{generation_id}/download")
    def download_generation(generation_id: int, db: Session = Depends(get_db)):
        item = db.scalar(select(PdfGeneration).where(PdfGeneration.id == generation_id))
        if not item:
            raise HTTPException(status_code=404, detail="Generated PDF not found")
        data = PdfStorage().get(item.storage_key)
        return Response(data, media_type="application/pdf", headers={
            "Content-Disposition": f'attachment; filename="{safe_filename(item.output_filename)}"',
            "Cache-Control": "private, no-store",
        })

    return router
