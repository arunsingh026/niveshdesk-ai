from __future__ import annotations

import base64
import hashlib
import io
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

import fitz
from cryptography.fernet import Fernet
from pypdf import PdfReader, PdfWriter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from ..config import settings


FIELD_HINTS = (
    "borrower name", "name", "address", "mobile", "phone", "e-mail", "email",
    "date", "file no", "loan a/c", "loan account", "loan limit", "s.b. a/c",
    "savings account", "flat no", "project name", "construction stage", "amount",
    "property", "payment in favour", "account no", "bank", "branch", "ifsc",
    "pan", "aadhaar", "city", "state", "pin code", "postcode",
)

CANONICAL_LABELS = (
    ("From", r"\b(?:from|flom)\b"),
    ("Borrower name", r"\bname\b"),
    ("File number", r"\bfi[lg].?\s*no\b"),
    ("Loan account", r"\bloa[mn]\s*a\s*[l1/\\v]?\s*c\b"),
    ("Loan limit", r"\bloan\s+limit\b"),
    ("Savings account", r"\b(?:s\.?\s*b\.?\s*a\s*[/\\]?\s*c|savings?\s*a\s*[il1/\\]?\s*c)\b"),
    ("Mobile", r"\b(?:mobile|mobine|modi)\b"),
    ("Email", r"\be[\s-]*mail\b"),
    ("Present construction stage", r"present\s*stage.*construction"),
    ("Flat number and project name", r"flat\s*no.*project\s*name"),
    ("Amount already released by bank", r"amount\s*already\s*released.*bank"),
    ("Margin paid to builder", r"margin\s*paid"),
    ("Amount requested now", r"amount\s*of?\s*release\s*requested\s*now"),
    ("Margin deficit savings account", r"debit.*savings\s*a\s*[/\\]?\s*c"),
    ("Property or builder address", r"address\s*of.*property.*builder"),
    ("Payment in favour of", r"payment\s*to\s*be\s*made\s*in\s*favour"),
    ("Builder or seller account", r"seller\s*a\s*[/\\]?\s*c\s*no"),
    ("Bank", r"\bbam?k"),
    ("Branch", r"\b(?:blam?ch|blanc)"),
    ("IFSC code", r"\bifsc\s*code"),
    ("Date", r"\bdate\b"),
)


def field_key(label: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
    return value[:110] or "field"


def safe_filename(name: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._ -]+", "", Path(name).name).strip(" .")
    return (stem or "document.pdf")[:240]


def _fernet() -> Fernet:
    seed = settings.pdf_value_encryption_key or settings.auth_code_pepper or settings.database_url
    key = base64.urlsafe_b64encode(hashlib.sha256(seed.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_value(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_value(value: str) -> str:
    return _fernet().decrypt(value.encode("ascii")).decode("utf-8")


class PdfStorage:
    def __init__(self) -> None:
        self.azure = bool(settings.azure_storage_connection_string)
        self.root = Path(settings.pdf_storage_path).expanduser().resolve()
        if not self.azure:
            self.root.mkdir(parents=True, exist_ok=True)

    def put(self, key: str, data: bytes) -> None:
        if self.azure:
            from azure.storage.blob import BlobServiceClient, ContentSettings
            service = BlobServiceClient.from_connection_string(settings.azure_storage_connection_string)
            container = service.get_container_client(settings.azure_pdf_container)
            try:
                container.create_container()
            except Exception:
                pass
            container.upload_blob(name=key, data=data, overwrite=True,
                                  content_settings=ContentSettings(content_type="application/pdf"))
            return
        path = (self.root / key).resolve()
        if self.root not in path.parents:
            raise ValueError("Invalid storage key")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get(self, key: str) -> bytes:
        if self.azure:
            from azure.storage.blob import BlobServiceClient
            service = BlobServiceClient.from_connection_string(settings.azure_storage_connection_string)
            return service.get_blob_client(settings.azure_pdf_container, key).download_blob().readall()
        path = (self.root / key).resolve()
        if self.root not in path.parents:
            raise ValueError("Invalid storage key")
        return path.read_bytes()

    def delete(self, key: str) -> None:
        if self.azure:
            from azure.storage.blob import BlobServiceClient
            service = BlobServiceClient.from_connection_string(settings.azure_storage_connection_string)
            service.get_blob_client(settings.azure_pdf_container, key).delete_blob(delete_snapshots="include")
            return
        path = (self.root / key).resolve()
        if self.root in path.parents:
            path.unlink(missing_ok=True)


def _unique_key(label: str, used: set[str]) -> str:
    root = field_key(label)
    key = root
    index = 2
    while key in used:
        key = f"{root}_{index}"
        index += 1
    used.add(key)
    return key


def _normalized_rect(rect: list[float], width: float, height: float, pdf_coordinates: bool) -> dict[str, float]:
    x0, y0, x1, y1 = [float(item) for item in rect]
    top = height - y1 if pdf_coordinates else y0
    return {
        "left": round(max(0, x0 / width), 5),
        "top": round(max(0, top / height), 5),
        "width": round(min(1, max(0.03, (x1 - x0) / width)), 5),
        "height": round(min(0.2, max(0.018, (y1 - y0) / height)), 5),
    }


def _acro_fields(reader: PdfReader) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    used: set[str] = set()
    for page_index, page in enumerate(reader.pages):
        width, height = float(page.mediabox.width), float(page.mediabox.height)
        for annotation_ref in page.get("/Annots", []):
            annotation = annotation_ref.get_object()
            if annotation.get("/Subtype") != "/Widget":
                continue
            parent = annotation.get("/Parent")
            source = parent.get_object() if parent else annotation
            name = str(source.get("/T") or annotation.get("/T") or "").strip()
            if not name:
                continue
            label = str(source.get("/TU") or name).replace("_", " ").strip()
            field_type = str(source.get("/FT") or annotation.get("/FT") or "/Tx")
            kind = "checkbox" if field_type == "/Btn" else "select" if field_type == "/Ch" else "text"
            rect = _normalized_rect(list(annotation.get("/Rect", [0, 0, width, 16])), width, height, True)
            key = _unique_key(name, used)
            fields.append({"key": key, "pdf_name": name, "label": label, "type": kind,
                           "page": page_index, **rect, "required": False, "source": "acroform"})
    return fields


def _line_candidates(page: fitz.Page, words: list[tuple], source: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[int, int], list[tuple]] = {}
    for word in words:
        grouped.setdefault((int(word[5]), int(word[6])), []).append(word)
    results: list[dict[str, Any]] = []
    used_labels: set[str] = set()
    blank_words = [word for word in words if len(str(word[4])) >= 14 and not re.search(r"\d", str(word[4]))]
    for line_words in grouped.values():
        line_words.sort(key=lambda item: item[0])
        text = " ".join(str(item[4]) for item in line_words).strip()
        lowered = text.lower()
        if not text or len(text) > 500:
            continue
        canonical = [(label, re.search(pattern, lowered, re.IGNORECASE)) for label, pattern in CANONICAL_LABELS]
        canonical = [(label, match) for label, match in canonical if match]
        if len(canonical) > 1:
            canonical = [(label, match) for label, match in canonical if label != "Borrower name"]
        if (any(label not in {"Bank", "Branch"} for label, _ in canonical) and
                not any(label == "Builder or seller account" for label, _ in canonical)):
            canonical = [(label, match) for label, match in canonical if label not in {"Bank", "Branch"}]
        if not canonical:
            has_colon = ":" in text
            has_blank = bool(re.search(r"[._]{3,}", text))
            matches = [hint for hint in FIELD_HINTS if hint in lowered]
            if not has_colon or (not has_blank and not matches):
                continue
            raw_label = text.split(":", 1)[0].strip(" ._-()")
            if (len(raw_label) < 2 or len(raw_label) > 55 or raw_label.isupper() or
                    any(skip in raw_label.lower() for skip in ("receipt", "request", "mail id"))):
                continue
            canonical = [(raw_label, re.match(r".*", lowered))]

        char_ends: list[int] = []
        position = 0
        for word in line_words:
            position += len(str(word[4]))
            char_ends.append(position)
            position += 1
        for label, match in canonical:
            if label.lower() in used_labels:
                continue
            used_labels.add(label.lower())
            match_end = match.end() if match else 0
            anchor_index = next((index for index, end in enumerate(char_ends) if end >= match_end), len(line_words) - 1)
            anchor = line_words[anchor_index]
            start_x = max(float(anchor[2]) + 5, page.rect.width * 0.15)
            next_matches = [item for item in canonical if item[1] and item[1].start() > (match.start() if match else 0)]
            if next_matches:
                next_start = min(item[1].start() for item in next_matches)
                next_index = next((index for index, end in enumerate(char_ends) if end >= next_start), len(line_words) - 1)
                right = max(start_x + 35, float(line_words[next_index][0]) - 8)
            else:
                right = page.rect.width - 24
            anchor_center = (float(anchor[1]) + float(anchor[3])) / 2
            nearby_blanks = [word for word in blank_words
                             if float(word[0]) >= float(anchor[2]) - 2 and
                             abs(((float(word[1]) + float(word[3])) / 2) - anchor_center) <= 20]
            if nearby_blanks:
                blank = min(nearby_blanks, key=lambda word: abs(((float(word[1]) + float(word[3])) / 2) - anchor_center) + abs(float(word[0]) - float(anchor[2])) * .03)
                start_x = max(20, float(blank[0]) + 2)
                right = min(page.rect.width - 20, float(blank[2]))
                anchor = blank
            if start_x > page.rect.width - 70:
                start_x = max(page.rect.width * 0.58, float(line_words[0][2]) + 5)
            top = max(0, float(anchor[1]) - 2)
            box_height = max(16, float(anchor[3] - anchor[1]) + 5)
            results.append({
                "label": label,
                "type": "date" if label == "Date" else "email" if label == "Email" else "text",
                "page": page.number,
                "left": round(start_x / page.rect.width, 5),
                "top": round(top / page.rect.height, 5),
                "width": round(max(35, right - start_x) / page.rect.width, 5),
                "height": round(min(0.08, box_height / page.rect.height), 5),
                "required": False,
                "source": source,
            })
    return results


def analyze_pdf(data: bytes) -> dict[str, Any]:
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        raise ValueError("Password-protected PDFs are not supported")
    if len(reader.pages) > settings.pdf_max_pages:
        raise ValueError(f"PDF has more than {settings.pdf_max_pages} pages")
    acro = _acro_fields(reader)
    signed = any(field.get("/FT") == "/Sig" for field in (reader.get_fields() or {}).values())
    doc = fitz.open(stream=data, filetype="pdf")
    page_sizes = [{"width": round(page.rect.width, 2), "height": round(page.rect.height, 2)} for page in doc]
    if acro:
        return {"fields": acro, "mode": "acroform", "page_count": len(reader.pages),
                "page_sizes": page_sizes, "signed": signed, "warnings": []}

    fields: list[dict[str, Any]] = []
    used: set[str] = set()
    used_ocr = False
    warnings: list[str] = []
    for page in doc:
        words = page.get_text("words")
        source = "text"
        if len(words) < 4:
            try:
                text_page = page.get_textpage_ocr(dpi=150, full=True)
                words = page.get_text("words", textpage=text_page)
                used_ocr = True
                source = "ocr"
            except Exception:
                warnings.append(f"Page {page.number + 1} needs manual field review because OCR is unavailable")
        for candidate in _line_candidates(page, words, source):
            candidate["key"] = _unique_key(candidate["label"], used)
            candidate["pdf_name"] = ""
            fields.append(candidate)
    if not fields:
        warnings.append("No fields were detected automatically. Add fields in the layout review before generating.")
    return {"fields": fields, "mode": "ocr" if used_ocr else "text", "page_count": len(reader.pages),
            "page_sizes": page_sizes, "signed": signed, "warnings": list(dict.fromkeys(warnings))}


def _fit_text(text: str, width: float, preferred: float = 9.0) -> float:
    size = preferred
    while size > 5.5 and stringWidth(text, "Helvetica", size) > width:
        size -= 0.4
    return size


def fill_pdf(original: bytes, fields: list[dict[str, Any]], values: dict[str, Any]) -> bytes:
    reader = PdfReader(io.BytesIO(original))
    if any(field.get("/FT") == "/Sig" for field in (reader.get_fields() or {}).values()):
        raise ValueError("This PDF is digitally signed. Filling it would invalidate the signature.")
    acro_values = {field["pdf_name"]: values.get(field["key"], "") for field in fields
                   if field.get("source") == "acroform" and field.get("pdf_name") and field["key"] in values}
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    if acro_values:
        writer.update_page_form_field_values(None, acro_values, auto_regenerate=True)

    by_page: dict[int, list[dict[str, Any]]] = {}
    for field in fields:
        if field.get("source") != "acroform" and field.get("key") in values:
            by_page.setdefault(int(field.get("page", 0)), []).append(field)
    for page_index, page_fields in by_page.items():
        if page_index < 0 or page_index >= len(writer.pages):
            continue
        target = writer.pages[page_index]
        width, height = float(target.mediabox.width), float(target.mediabox.height)
        buffer = io.BytesIO()
        overlay = canvas.Canvas(buffer, pagesize=(width, height))
        overlay.setFillColorRGB(0.02, 0.08, 0.30)
        for field in page_fields:
            value = str(values.get(field["key"], "")).strip()
            if not value:
                continue
            left = float(field.get("left", 0.35)) * width
            top = float(field.get("top", 0.1)) * height
            box_width = max(30, float(field.get("width", 0.5)) * width)
            box_height = max(10, float(field.get("height", 0.025)) * height)
            size = _fit_text(value, box_width, min(10.0, max(7.0, box_height * 0.62)))
            overlay.setFont("Helvetica", size)
            overlay.drawString(left, height - top - min(box_height * 0.72, size + 2) + 3, value)
        overlay.save()
        buffer.seek(0)
        target.merge_page(PdfReader(buffer).pages[0])

    output = io.BytesIO()
    writer.write(output)
    result = output.getvalue()
    check = PdfReader(io.BytesIO(result))
    if len(check.pages) != len(reader.pages):
        raise ValueError("Generated PDF failed page-count validation")
    return result


def new_storage_key(user_id: int, category: str, filename: str) -> str:
    return f"users/{user_id}/{category}/{uuid4().hex}/{safe_filename(filename)}"
