from __future__ import annotations

import json
from typing import Any

from src.config import get_settings
from src.deepseek_client import DeepSeekClient
from src.glossary import glossary_prompt_block
from src.metadata_detection import metadata_by_page
from src.utils import append_jsonl, read_json, read_jsonl, setup_logging, safe_preview


SYSTEM_PROMPT = """You are a careful Telugu-to-English Ramayana translator.
Translate only from the supplied Telugu source. Preserve the religious, mythological,
cultural, theological, and narrative meaning. Do not modernize away devotional tone.
Do not invent missing content. If OCR text is unclear, mark uncertainty in translation_notes.
Return strict JSON only."""


def _json_value(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _translation_prompt(record: dict[str, Any], metadata: dict[str, Any], glossary_block: str) -> str:
    return f"""
{glossary_block}

Metadata context:
- page_number: {record.get('page_number')}
- kanda: {metadata.get('kanda')}
- chapter_number: {metadata.get('chapter_number')}
- chapter_title: {metadata.get('chapter_title')}
- sarga_range: {metadata.get('sarga_range')}
- extraction_notes: {record.get('notes') or ''}
- quality_flags: {record.get('quality_flags') or []}

Translate this cleaned Telugu source into faithful English. Preserve Q&A structure if present.
Return this exact JSON shape:
{{
  "page_number": {record.get('page_number')},
  "source_file": "ramayana.pdf",
  "kanda": {_json_value(metadata.get('kanda'))},
  "chapter_number": {_json_value(metadata.get('chapter_number'))},
  "chapter_title": {_json_value(metadata.get('chapter_title'))},
  "sarga_range": {_json_value(metadata.get('sarga_range'))},
  "original_telugu_cleaned": "...",
  "english_translation": "...",
  "summary": "...",
  "keywords": ["..."],
  "entities": {{"people": [], "places": [], "concepts": []}},
  "translation_notes": "...",
  "model": "..."
}}

Cleaned Telugu source:
{record.get('cleaned_text') or ''}
""".strip()


def translate_pages(limit: int | None = None) -> list[dict[str, Any]]:
    settings = get_settings()
    logger = setup_logging(settings.logs_dir, "translate_with_deepseek")
    settings.require_deepseek_key()
    records = read_jsonl(settings.pages_cleaned)
    if not records:
        raise FileNotFoundError(f"Missing {settings.pages_cleaned}. Run --clean first.")
    metadata = read_json(settings.metadata_map, default={}) or {}
    by_page = metadata_by_page(metadata)
    glossary_block = glossary_prompt_block()
    client = DeepSeekClient.from_env(logger=logger)

    existing = read_jsonl(settings.translated_pages)
    translated_page_numbers = {int(record["page_number"]) for record in existing if record.get("page_number")}
    translated = list(existing)

    processed = 0
    for record in records:
        page_number = int(record["page_number"])
        if page_number in translated_page_numbers:
            logger.info("Skipping page %s; already translated.", page_number)
            continue
        if not (record.get("cleaned_text") or "").strip():
            logger.warning("Skipping empty cleaned page %s", page_number)
            continue

        page_metadata = by_page.get(page_number, {})
        user_prompt = _translation_prompt(record, page_metadata, glossary_block)
        response = client.json_completion(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]
        )
        response.setdefault("page_number", page_number)
        response.setdefault("source_file", settings.ramayana_pdf.name)
        response.setdefault("kanda", page_metadata.get("kanda"))
        response.setdefault("chapter_number", page_metadata.get("chapter_number"))
        response.setdefault("chapter_title", page_metadata.get("chapter_title"))
        response.setdefault("sarga_range", page_metadata.get("sarga_range"))
        response.setdefault("original_telugu_cleaned", record.get("cleaned_text", ""))
        response.setdefault("model", settings.deepseek_model)
        response["source_preview"] = safe_preview(record.get("cleaned_text", ""))

        append_jsonl(settings.translated_pages, response)
        translated.append(response)
        processed += 1
        logger.info("Translated page %s", page_number)
        if limit and processed >= limit:
            break

    return translated


if __name__ == "__main__":
    translate_pages()
