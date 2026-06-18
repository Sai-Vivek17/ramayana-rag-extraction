from __future__ import annotations

from src.config import get_settings
from src.inspect_pdf import _import_fitz, inspect_pdf
from src.utils import read_json, setup_logging, telugu_char_count, telugu_ratio, write_jsonl


def _pdfplumber_text(pdf_path, page_index: int) -> str:
    try:
        import pdfplumber
    except ImportError:
        return ""

    try:
        with pdfplumber.open(pdf_path) as pdf:
            if page_index >= len(pdf.pages):
                return ""
            return pdf.pages[page_index].extract_text() or ""
    except Exception:
        return ""


def extract_pdf_text() -> list[dict]:
    settings = get_settings()
    logger = setup_logging(settings.logs_dir, "extract_pdf")
    settings.require_ramayana_pdf()
    fitz = _import_fitz()

    report = read_json(settings.inspection_report)
    if not report:
        report = inspect_pdf()
    inspection_by_page = {page["page_number"]: page for page in report.get("pages", [])}

    doc = fitz.open(settings.ramayana_pdf)
    records: list[dict] = []
    for index, page in enumerate(doc, start=1):
        raw_text = page.get_text("text") or ""
        extraction_method = "pymupdf"
        notes: list[str] = []

        if len(raw_text.strip()) < 40 or telugu_ratio(raw_text) < 0.08:
            fallback = _pdfplumber_text(settings.ramayana_pdf, index - 1)
            if len(fallback.strip()) > len(raw_text.strip()):
                raw_text = fallback
                extraction_method = "pdfplumber"
                notes.append("pdfplumber fallback produced more text than PyMuPDF.")

        inspection = inspection_by_page.get(index, {})
        needs_ocr = bool(inspection.get("ocr_recommended")) or len(raw_text.strip()) < 20 or telugu_ratio(raw_text) < 0.08
        if needs_ocr:
            notes.append("OCR recommended by inspection or weak embedded text.")

        records.append(
            {
                "page_number": index,
                "source_file": settings.ramayana_pdf.name,
                "raw_text": raw_text,
                "extraction_method": extraction_method,
                "char_count": len(raw_text),
                "telugu_char_count": telugu_char_count(raw_text),
                "telugu_ratio": round(telugu_ratio(raw_text), 4),
                "needs_ocr": needs_ocr,
                "notes": " ".join(notes).strip(),
            }
        )

    write_jsonl(settings.pages_raw, records)
    logger.info("Wrote %s page records to %s", len(records), settings.pages_raw)
    return records


if __name__ == "__main__":
    extract_pdf_text()

