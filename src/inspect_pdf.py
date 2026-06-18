from __future__ import annotations

from dataclasses import asdict, dataclass

from src.config import get_settings
from src.utils import atomic_write_json, setup_logging, telugu_char_count, telugu_ratio


@dataclass
class PageInspection:
    page_number: int
    extracted_text_length: int
    telugu_char_count: int
    telugu_ratio: float
    image_count: int
    classification: str
    ocr_recommended: bool
    notes: str


def _import_fitz():
    try:
        import fitz  # type: ignore

        return fitz
    except ImportError as exc:
        raise ImportError(
            "PyMuPDF is required for PDF inspection. Install dependencies with "
            "`pip install -r requirements.txt`."
        ) from exc


def classify_page(text: str, image_count: int) -> tuple[str, bool, str]:
    length = len((text or "").strip())
    ratio = telugu_ratio(text)
    nonspace = len("".join((text or "").split()))
    punctuation_noise = 0.0
    if nonspace:
        noisy = sum(1 for ch in text if not ch.isalnum() and not ch.isspace() and ch not in ".,;:!?()[]{}\"'/-")
        punctuation_noise = noisy / nonspace

    if length < 20 and image_count > 0:
        return "scanned", True, "Very little embedded text and images are present."
    if length < 20:
        return "weak_text", True, "Very little embedded text was extracted."
    if ratio < 0.08 and length > 80:
        return "garbled", True, "Embedded text has low Telugu ratio and may be encoded or noisy."
    if punctuation_noise > 0.25 and ratio < 0.35:
        return "garbled", True, "Text contains a high symbol/noise ratio."
    if image_count > 0 and length > 80:
        return "mixed", ratio < 0.35, "Page has both extractable text and images."
    return "text_based", False, "Embedded text appears extractable."


def inspect_pdf() -> dict:
    settings = get_settings()
    logger = setup_logging(settings.logs_dir, "inspect_pdf")
    settings.require_ramayana_pdf()
    fitz = _import_fitz()

    logger.info("Inspecting %s", settings.ramayana_pdf)
    doc = fitz.open(settings.ramayana_pdf)
    pages: list[PageInspection] = []

    for index, page in enumerate(doc, start=1):
        text = page.get_text("text") or ""
        images = page.get_images(full=True)
        classification, ocr_recommended, notes = classify_page(text, len(images))
        pages.append(
            PageInspection(
                page_number=index,
                extracted_text_length=len(text.strip()),
                telugu_char_count=telugu_char_count(text),
                telugu_ratio=round(telugu_ratio(text), 4),
                image_count=len(images),
                classification=classification,
                ocr_recommended=ocr_recommended,
                notes=notes,
            )
        )

    page_dicts = [asdict(page) for page in pages]
    summary = {
        "source_file": settings.ramayana_pdf.name,
        "total_pages": len(doc),
        "text_based_pages": sum(1 for page in pages if page.classification == "text_based"),
        "scanned_pages": sum(1 for page in pages if page.classification == "scanned"),
        "mixed_pages": sum(1 for page in pages if page.classification == "mixed"),
        "garbled_or_weak_pages": sum(1 for page in pages if page.classification in {"garbled", "weak_text"}),
        "ocr_recommended_pages": sum(1 for page in pages if page.ocr_recommended),
    }
    report = {"summary": summary, "pages": page_dicts}
    atomic_write_json(settings.inspection_report, report)
    logger.info("Wrote inspection report to %s", settings.inspection_report)
    return report


if __name__ == "__main__":
    inspect_pdf()

