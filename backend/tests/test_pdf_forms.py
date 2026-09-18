import io
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from pypdf import PdfReader
from reportlab.pdfgen import canvas
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.db import Base
from app.services.pdf_forms import analyze_pdf, decrypt_value, encrypt_value, fill_pdf


def fillable_pdf() -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(595, 842))
    pdf.drawString(60, 780, "Borrower name:")
    pdf.acroForm.textfield(name="borrower_name", tooltip="Borrower name", x=175, y=765, width=260, height=24)
    pdf.drawString(60, 730, "Email:")
    pdf.acroForm.textfield(name="email", tooltip="Email address", x=175, y=715, width=260, height=24)
    pdf.save()
    return buffer.getvalue()


def text_pdf() -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(595, 842))
    pdf.drawString(60, 780, "Name: ______________________________")
    pdf.drawString(60, 740, "Mobile: ____________________________")
    pdf.save()
    return buffer.getvalue()


def test_acroform_analysis_and_generation_preserve_original():
    original = fillable_pdf()
    analysis = analyze_pdf(original)
    assert analysis["mode"] == "acroform"
    assert {field["pdf_name"] for field in analysis["fields"]} == {"borrower_name", "email"}

    values = {field["key"]: "Nootan Singh" if field["pdf_name"] == "borrower_name" else "user@example.com"
              for field in analysis["fields"]}
    result = fill_pdf(original, analysis["fields"], values)
    fields = PdfReader(io.BytesIO(result)).get_fields()
    assert fields["borrower_name"]["/V"] == "Nootan Singh"
    assert fields["email"]["/V"] == "user@example.com"
    assert original != result
    assert len(PdfReader(io.BytesIO(original)).pages) == len(PdfReader(io.BytesIO(result)).pages) == 1


def test_text_form_analysis_and_overlay_generation():
    original = text_pdf()
    analysis = analyze_pdf(original)
    assert analysis["mode"] == "text"
    labels = {field["label"].lower() for field in analysis["fields"]}
    assert "borrower name" in labels and "mobile" in labels
    values = {field["key"]: "Arun" if field["label"].lower() == "borrower name" else "7710873730"
              for field in analysis["fields"]}
    result = fill_pdf(original, analysis["fields"], values)
    assert len(PdfReader(io.BytesIO(result)).pages) == 1
    assert b"Arun" in result or len(result) > len(original)


def test_saved_value_encryption_round_trip():
    encrypted = encrypt_value("446176411212")
    assert encrypted != "446176411212"
    assert "446176411212" not in encrypted
    assert decrypt_value(encrypted) == "446176411212"


def test_pdf_api_reuses_template_memory_and_isolates_users(monkeypatch, tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(main, "SessionLocal", factory)
    monkeypatch.setattr(main.settings, "resend_api_key", "")
    monkeypatch.setattr(main.settings, "auth_code_pepper", "test-pdf-pepper")
    monkeypatch.setattr(main.settings, "pdf_storage_path", str(tmp_path / "pdfs"))

    first, second = TestClient(main.app), TestClient(main.app)
    for client, email, phone in ((first, "first-pdf@example.com", "+919876543200"), (second, "second-pdf@example.com", "+919876543201")):
        response = client.post("/api/auth/register", json={
            "full_name": "PDF User", "email": email, "phone": phone, "password": "StrongPass9",
        })
        assert response.status_code == 201

    source = fillable_pdf()
    uploaded = first.post("/api/pdf-forms/upload", data={"name": "Loan form"},
                          files={"file": ("loan.pdf", source, "application/pdf")})
    assert uploaded.status_code == 201
    detail = uploaded.json()["template"]
    template_id = detail["id"]
    assert detail["field_count"] == 2
    assert second.get(f"/api/pdf-forms/{template_id}").status_code == 404

    values = {field["key"]: "Nootan Singh" if field["pdf_name"] == "borrower_name" else "user@example.com"
              for field in detail["fields"]}
    generated = first.post(f"/api/pdf-forms/{template_id}/generate", json={
        "values": values, "remember_keys": list(values),
    })
    assert generated.status_code == 201
    downloaded = first.get(generated.json()["download_url"])
    assert downloaded.status_code == 200
    assert downloaded.headers["content-type"] == "application/pdf"
    reopened = first.get(f"/api/pdf-forms/{template_id}").json()
    assert reopened["suggestions"] == values

    reused = first.post("/api/pdf-forms/upload", files={"file": ("loan-again.pdf", source, "application/pdf")})
    assert reused.status_code == 201 and reused.json()["reused"] is True
    assert len(first.get("/api/pdf-forms").json()) == 1
    assert second.get("/api/pdf-forms").json() == []
