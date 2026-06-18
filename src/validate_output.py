from __future__ import annotations

from collections import Counter
from typing import Any

from src.config import get_settings
from src.glossary import find_glossary_inconsistencies
from src.utils import atomic_write_json, has_telugu, read_jsonl, setup_logging, word_count_english

REQUIRED_FIELDS = [
    "chunk_id",
    "source_file",
    "kanda",
    "chapter_number",
    "chapter_title",
    "page_start",
    "page_end",
    "sequence_number",
    "original_telugu_cleaned",
    "english_translation",
    "summary",
    "keywords",
    "entities",
]


def validate_chunks(chunks: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    ids = [chunk.get("chunk_id") for chunk in chunks]
    counts = Counter(ids)

    for index, chunk in enumerate(chunks, start=1):
        location = {"index": index, "chunk_id": chunk.get("chunk_id")}
        for field in REQUIRED_FIELDS:
            if field not in chunk:
                errors.append({**location, "field": field, "message": "Missing required field."})
        if not chunk.get("chunk_id"):
            errors.append({**location, "field": "chunk_id", "message": "Empty chunk_id."})
        elif counts[chunk.get("chunk_id")] > 1:
            errors.append({**location, "field": "chunk_id", "message": "Duplicate chunk_id."})

        if not chunk.get("original_telugu_cleaned"):
            errors.append({**location, "field": "original_telugu_cleaned", "message": "Empty Telugu source."})
        if not chunk.get("english_translation"):
            errors.append({**location, "field": "english_translation", "message": "Empty English translation."})

        words = int(chunk.get("word_count") or word_count_english(chunk.get("english_translation", "")))
        if words < 50:
            warnings.append({**location, "field": "word_count", "message": f"Chunk is very small ({words} words)."})
        elif words > 850:
            warnings.append({**location, "field": "word_count", "message": f"Chunk is very large ({words} words)."})

        if has_telugu(chunk.get("english_translation", "")):
            warnings.append({**location, "field": "english_translation", "message": "Telugu characters found in English."})

        if chunk.get("kanda") is None or chunk.get("chapter_number") is None:
            warnings.append({**location, "field": "metadata", "message": "Missing Kanda or chapter metadata."})

        page_start = chunk.get("page_start")
        page_end = chunk.get("page_end")
        if page_start is None or page_end is None:
            errors.append({**location, "field": "page_range", "message": "Missing page_start/page_end."})
        elif int(page_start) > int(page_end):
            errors.append({**location, "field": "page_range", "message": "Invalid page range."})

        if not chunk.get("keywords"):
            warnings.append({**location, "field": "keywords", "message": "Empty keywords."})
        entities = chunk.get("entities") or {}
        if not any(entities.get(key) for key in ["people", "places", "concepts"]):
            warnings.append({**location, "field": "entities", "message": "Empty entities."})

        for issue in find_glossary_inconsistencies(chunk.get("english_translation", "")):
            warnings.append({**location, "field": "glossary", "message": issue})

        if "uncertain" in (chunk.get("notes") or "").lower() and not chunk.get("notes"):
            warnings.append({**location, "field": "notes", "message": "Uncertainty should be explained in notes."})

    sequence_numbers = [chunk.get("sequence_number") for chunk in chunks if chunk.get("sequence_number") is not None]
    expected = list(range(1, len(sequence_numbers) + 1))
    if sequence_numbers != expected:
        warnings.append({"field": "sequence_number", "message": "Sequence numbers are not continuous from 1."})

    return {
        "ok": not errors,
        "total_chunks": len(chunks),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }


def validate_output() -> dict[str, Any]:
    settings = get_settings()
    logger = setup_logging(settings.logs_dir, "validate_output")
    chunks = read_jsonl(settings.chunks_jsonl)
    if not chunks:
        raise FileNotFoundError(f"Missing or empty chunks file: {settings.chunks_jsonl}. Run --chunk first.")

    report = validate_chunks(chunks)
    atomic_write_json(settings.validation_report, report)
    logger.info(
        "Validation complete: %s errors, %s warnings",
        report["error_count"],
        report["warning_count"],
    )
    print(f"Validation: {report['error_count']} errors, {report['warning_count']} warnings, {report['total_chunks']} chunks")
    return report


if __name__ == "__main__":
    validate_output()
