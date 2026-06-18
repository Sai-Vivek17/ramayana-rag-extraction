from __future__ import annotations

import re
from typing import Any

from src.config import get_settings
from src.utils import atomic_write_json, read_jsonl, setup_logging


KANDA_PATTERNS: list[tuple[str, list[str]]] = [
    ("Bala Kanda", ["బాలకాండ", "బాల కాండ", "bala kanda"]),
    ("Ayodhya Kanda", ["అయోధ్యకాండ", "అయోధ్య కాండ", "ayodhya kanda"]),
    ("Aranya Kanda", ["అరణ్యకాండ", "అరణ్య కాండ", "aranya kanda"]),
    ("Kishkindha Kanda", ["కిష్కింధకాండ", "కిష్కింధ కాండ", "kishkindha kanda", "kishkinda kanda"]),
    ("Sundara Kanda", ["సుందరకాండ", "సుందర కాండ", "sundara kanda"]),
    ("Yuddha Kanda", ["యుద్ధకాండ", "యుద్ధ కాండ", "yuddha kanda", "lanka kanda"]),
    ("Uttara Kanda", ["ఉత్తరకాండ", "ఉత్తర కాండ", "uttara kanda"]),
]

TELUGU_ORDINALS = {
    "మొదటి": 1,
    "రెండవ": 2,
    "రెండవది": 2,
    "మూడవ": 3,
    "నాల్గవ": 4,
    "నాలుగవ": 4,
    "ఐదవ": 5,
    "ఆరవ": 6,
    "ఏడవ": 7,
    "ఎనిమిదవ": 8,
    "తొమ్మిదవ": 9,
    "పదవ": 10,
}

CHAPTER_PATTERNS = [
    re.compile(r"(?:chapter|చాప్టర్|అధ్యాయము|అధ్యాయం)\s*[-:]?\s*(\d{1,3})", re.IGNORECASE),
    re.compile(r"(\d{1,3})\s*(?:వ|వది|వ అధ్యాయము|వ అధ్యాయం)"),
]

SARGA_PATTERNS = [
    re.compile(r"(?:sarga|సర్గ|సర్గలు)\s*[-:]?\s*(\d{1,3}\s*(?:-|–|to|నుండి)\s*\d{1,3}|\d{1,3})", re.IGNORECASE),
    re.compile(r"(\d{1,3}\s*[-–]\s*\d{1,3})\s*(?:సర్గ|సర్గలు)", re.IGNORECASE),
]


def detect_kanda(text: str) -> str | None:
    normalized = (text or "").lower().replace(" ", "")
    for canonical, patterns in KANDA_PATTERNS:
        for pattern in patterns:
            if pattern.lower().replace(" ", "") in normalized:
                return canonical
    return None


def detect_chapter_number(text: str) -> int | None:
    text = text or ""
    for pattern in CHAPTER_PATTERNS:
        match = pattern.search(text)
        if match:
            return int(match.group(1))
    for word, number in TELUGU_ORDINALS.items():
        if word in text and ("అధ్యాయ" in text or "చాప్టర్" in text):
            return number
    return None


def detect_sarga_range(text: str) -> str | None:
    text = text or ""
    for pattern in SARGA_PATTERNS:
        match = pattern.search(text)
        if match:
            return re.sub(r"\s+", "", match.group(1)).replace("–", "-").replace("to", "-")
    return None


def detect_chapter_title(text: str) -> str | None:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    for line in lines[:8]:
        if len(line) > 120:
            continue
        if any(token in line for token in ["అధ్యాయ", "చాప్టర్", "సర్గ", "కాండ"]):
            return line
    return None


def build_metadata_map() -> dict[str, Any]:
    settings = get_settings()
    logger = setup_logging(settings.logs_dir, "metadata_detection")
    records = read_jsonl(settings.pages_cleaned)
    if not records:
        raise FileNotFoundError(f"Missing {settings.pages_cleaned}. Run --clean first.")

    current_kanda: str | None = None
    current_chapter: int | None = None
    current_title: str | None = None
    current_sarga: str | None = None
    pages: list[dict[str, Any]] = []

    for sequence, record in enumerate(records, start=1):
        text = record.get("cleaned_text") or record.get("raw_text") or ""
        kanda = detect_kanda(text)
        chapter = detect_chapter_number(text)
        title = detect_chapter_title(text)
        sarga = detect_sarga_range(text)

        if kanda:
            current_kanda = kanda
        if chapter:
            current_chapter = chapter
        if title:
            current_title = title
        if sarga:
            current_sarga = sarga

        needs_review = any(value is None for value in [current_kanda, current_chapter]) or bool(record.get("quality_flags"))
        pages.append(
            {
                "page_number": record["page_number"],
                "sequence_number": sequence,
                "kanda": current_kanda,
                "chapter_number": current_chapter,
                "chapter_title": current_title,
                "sarga_range": current_sarga,
                "source_confidence": "detected" if not needs_review else "needs_review",
                "needs_review": needs_review,
                "notes": "Automatically detected from page text; edit this map if needed.",
            }
        )

    kandas = sorted({page["kanda"] for page in pages if page["kanda"]})
    metadata = {
        "source_file": settings.ramayana_pdf.name,
        "description": "Human-editable metadata map generated from cleaned Telugu pages.",
        "kandas_detected": kandas,
        "pages": pages,
    }
    atomic_write_json(settings.metadata_map, metadata)
    logger.info("Wrote metadata map to %s", settings.metadata_map)
    return metadata


def metadata_by_page(metadata: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {int(page["page_number"]): page for page in metadata.get("pages", [])}


if __name__ == "__main__":
    build_metadata_map()

