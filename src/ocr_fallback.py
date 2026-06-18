from __future__ import annotations

from io import BytesIO

from PIL import Image

from src.config import get_settings
from src.extract_pdf import extract_pdf_text
from src.inspect_pdf import _import_fitz
from src.utils import read_jsonl, setup_logging, telugu_char_count, telugu_ratio, write_jsonl


def _configure_tesseract(tesseract_cmd: str) -> None:
    try:
        import pytesseract
    except ImportError as exc:
        raise ImportError(
            "pytesseract is required for OCR fallback. Install dependencies and Tesseract OCR "
            "with Telugu traineddata before running --ocr."
        ) from exc
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd


def _ocr_page(page, zoom: float = 2.0) -> str:
    import pytesseract

    matrix = page.get_pixmap(matrix=_page_matrix(page, zoom), alpha=False)
    image = Image.open(BytesIO(matrix.tobytes("png")))
    return pytesseract.image_to_string(image, lang="tel", config="--psm 6") or ""


def _page_matrix(page, zoom: float):
    fitz = _import_fitz()
    return fitz.Matrix(zoom, zoom)


def run_ocr_fallback(force: bool = False) -> list[dict]:
    settings = get_settings()
    logger = setup_logging(settings.logs_dir, "ocr_fallback")
    settings.require_ramayana_pdf()
    _configure_tesseract(settings.tesseract_cmd)
    fitz = _import_fitz()

    records = read_jsonl(settings.pages_raw)
    if not records:
        records = extract_pdf_text()

    doc = fitz.open(settings.ramayana_pdf)
    updated: list[dict] = []
    ocr_count = 0
    for record in records:
        page_number = int(record["page_number"])
        should_ocr = force or bool(record.get("needs_ocr")) or int(record.get("telugu_char_count") or 0) < 10
        if not should_ocr:
            updated.append(record)
            continue

        page = doc[page_number - 1]
        try:
            ocr_text = _ocr_page(page)
        except Exception as exc:
            record["notes"] = f"{record.get('notes', '')} OCR failed: {exc}".strip()
            updated.append(record)
            logger.warning("OCR failed on page %s: %s", page_number, exc)
            continue

        existing_text = record.get("raw_text", "")
        existing_score = telugu_char_count(existing_text), len(existing_text)
        ocr_score = telugu_char_count(ocr_text), len(ocr_text)
        if ocr_score > existing_score:
            record["raw_text"] = ocr_text
            record["extraction_method"] = (
                "pymupdf_plus_ocr" if record.get("extraction_method") == "pymupdf" else "ocr_tesseract_tel"
            )
            record["char_count"] = len(ocr_text)
            record["telugu_char_count"] = telugu_char_count(ocr_text)
            record["telugu_ratio"] = round(telugu_ratio(ocr_text), 4)
            record["needs_ocr"] = False
            record["notes"] = f"{record.get('notes', '')} OCR text accepted.".strip()
            ocr_count += 1
        else:
            record["notes"] = f"{record.get('notes', '')} OCR attempted but embedded text was retained.".strip()
        updated.append(record)
        write_jsonl(settings.pages_raw, updated + records[len(updated) :])

    write_jsonl(settings.pages_raw, updated)
    logger.info("OCR fallback updated %s pages", ocr_count)
    return updated


if __name__ == "__main__":
    run_ocr_fallback()

