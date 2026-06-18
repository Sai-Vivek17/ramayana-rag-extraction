from __future__ import annotations

import re
import unicodedata

from src.config import get_settings
from src.utils import read_jsonl, setup_logging, telugu_char_count, telugu_ratio, write_jsonl

PAGE_NUMBER_RE = re.compile(r"^\s*(?:[ivxlcdmIVXLCDM]+|\d{1,4})\s*$")
SYMBOL_NOISE_RE = re.compile(r"[�\uFFFD]+")
PRIVATE_USE_RE = re.compile(r"[\uE000-\uF8FF]+")
REPEATED_PUNCT_RE = re.compile(r"([.।,;:!?])\1{2,}")
EXCESS_SPACES_RE = re.compile(r"[ \t]{2,}")
TELUGU_LETTER_RE = re.compile(r"[\u0C00-\u0C7F]")


def _line_has_telugu(line: str) -> bool:
    return bool(TELUGU_LETTER_RE.search(line))


def clean_telugu_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text or "")
    text = SYMBOL_NOISE_RE.sub("", text)
    text = PRIVATE_USE_RE.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)

    cleaned_lines: list[str] = []
    for line in text.splitlines():
        line = unicodedata.normalize("NFC", line).strip()
        if not line:
            if cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")
            continue
        line = EXCESS_SPACES_RE.sub(" ", line)
        line = REPEATED_PUNCT_RE.sub(r"\1", line)

        if PAGE_NUMBER_RE.match(line):
            continue
        if len(line) <= 3 and not _line_has_telugu(line):
            continue
        # Remove decorative or printer artifact lines without Telugu or useful ASCII content.
        useful_ascii = re.search(r"[A-Za-z0-9]", line)
        if not _line_has_telugu(line) and not useful_ascii and len(line) < 20:
            continue
        cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_pages() -> list[dict]:
    settings = get_settings()
    logger = setup_logging(settings.logs_dir, "clean_telugu_text")
    records = read_jsonl(settings.pages_raw)
    if not records:
        raise FileNotFoundError(f"Missing {settings.pages_raw}. Run --extract first.")

    cleaned: list[dict] = []
    for record in records:
        cleaned_text = clean_telugu_text(record.get("raw_text", ""))
        quality_flags: list[str] = []
        if len(cleaned_text) < 20:
            quality_flags.append("very_short_cleaned_text")
        if telugu_ratio(cleaned_text) < 0.08:
            quality_flags.append("low_telugu_ratio_after_cleaning")
        if record.get("needs_ocr"):
            quality_flags.append("ocr_recommended")

        new_record = dict(record)
        new_record["cleaned_text"] = cleaned_text
        new_record["cleaned_char_count"] = len(cleaned_text)
        new_record["cleaned_telugu_char_count"] = telugu_char_count(cleaned_text)
        new_record["cleaned_telugu_ratio"] = round(telugu_ratio(cleaned_text), 4)
        new_record["quality_flags"] = quality_flags
        cleaned.append(new_record)

    write_jsonl(settings.pages_cleaned, cleaned)
    logger.info("Wrote cleaned Telugu pages to %s", settings.pages_cleaned)
    return cleaned


if __name__ == "__main__":
    clean_pages()
