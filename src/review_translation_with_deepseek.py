from __future__ import annotations

from typing import Any

from src.config import get_settings
from src.deepseek_client import DeepSeekClient, DeepSeekError
from src.glossary import glossary_prompt_block
from src.utils import append_jsonl, read_jsonl, setup_logging


SYSTEM_PROMPT = """You are reviewing a Telugu-to-English Ramayana translation.
Compare the Telugu source and English translation carefully. Preserve theology,
relationships, names, and devotional tone. Return strict JSON only."""


def _review_prompt(record: dict[str, Any], glossary_block: str) -> str:
    return f"""
{glossary_block}

Review this translation against the Telugu source.
Check for missing meaning, wrong names, broken theological/cultural context,
mistranslated relationships, unnatural English, and glossary inconsistency.
Return JSON:
{{
  "page_number": {record.get('page_number')},
  "quality_score": 0-100,
  "issues": ["up to five concise issues"],
  "corrected_translation": "only provide a corrected full translation if serious errors require it; otherwise use an empty string",
  "review_notes": "concise notes, no more than 120 words",
  "review_model": "..."
}}

Telugu source:
{record.get('original_telugu_cleaned') or ''}

Current English translation:
{record.get('english_translation') or ''}
""".strip()


def review_translations(limit: int | None = None) -> list[dict[str, Any]]:
    settings = get_settings()
    logger = setup_logging(settings.logs_dir, "review_translation_with_deepseek")
    if not settings.enable_review_pass:
        logger.info("ENABLE_REVIEW_PASS is false; skipping DeepSeek review.")
        return read_jsonl(settings.translated_pages)

    settings.require_deepseek_key()
    translated = read_jsonl(settings.translated_pages)
    if not translated:
        raise FileNotFoundError(f"Missing {settings.translated_pages}. Run --translate first.")

    existing = read_jsonl(settings.reviewed_pages)
    reviewed_page_numbers = {int(record["page_number"]) for record in existing if record.get("page_number")}
    reviewed = list(existing)
    client = DeepSeekClient.from_env(logger=logger)
    glossary_block = glossary_prompt_block()

    processed = 0
    for record in translated:
        page_number = int(record["page_number"])
        if page_number in reviewed_page_numbers:
            continue

        try:
            review = client.json_completion(
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": _review_prompt(record, glossary_block)},
                ]
            )
        except DeepSeekError as exc:
            logger.warning("Review failed for page %s; preserving translation for manual review: %s", page_number, exc)
            review = {
                "page_number": page_number,
                "quality_score": None,
                "issues": ["DeepSeek review response could not be parsed; manual review recommended."],
                "corrected_translation": "",
                "review_notes": "The original DeepSeek translation was preserved because the review response was malformed or truncated.",
                "review_model": settings.deepseek_model,
                "needs_manual_review": True,
            }
        merged: dict[str, Any] = dict(record)
        merged["review"] = review
        if review.get("corrected_translation"):
            merged["english_translation"] = review["corrected_translation"]
            merged["translation_notes"] = f"{merged.get('translation_notes', '')} Reviewed and corrected by DeepSeek.".strip()
        merged["review_model"] = settings.deepseek_model
        append_jsonl(settings.reviewed_pages, merged)
        reviewed.append(merged)
        processed += 1
        logger.info("Reviewed page %s", page_number)
        if limit and processed >= limit:
            break

    return reviewed


if __name__ == "__main__":
    review_translations()
