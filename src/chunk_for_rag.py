from __future__ import annotations

import json
import re
from typing import Any

from src.config import get_settings
from src.glossary import load_transliteration_rules
from src.utils import (
    merge_entities,
    read_jsonl,
    setup_logging,
    stable_hash,
    stable_slug,
    unique_ordered,
    word_count_english,
    write_csv,
    write_jsonl,
)

TARGET_MIN_WORDS = 300
TARGET_MAX_WORDS = 700


def make_chunk_id(kanda: str | None, chapter_number: int | None, sequence_number: int) -> str:
    kanda_slug = stable_slug(kanda or "unknown_kanda", "unknown_kanda")
    chapter = f"chapter_{int(chapter_number):03d}" if chapter_number is not None else "chapter_unknown"
    return f"{kanda_slug}_{chapter}_chunk_{sequence_number:03d}"


def _standardize_english_terms(text: str) -> str:
    rules = load_transliteration_rules()
    normalizations = rules.get("normalizations", {})
    result = text or ""
    for canonical, variants in normalizations.items():
        for variant in variants:
            if not variant or variant == canonical:
                continue
            result = re.sub(rf"\b{re.escape(variant)}\b", canonical, result)
    return result


def _normalize_english_punctuation(text: str) -> str:
    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
        "\u00a0": " ",
    }
    result = text or ""
    for source, target in replacements.items():
        result = result.replace(source, target)
    return result


def _remove_telugu_inline_notes(text: str) -> tuple[str, list[str]]:
    notes: list[str] = []

    def replace_note(match: re.Match[str]) -> str:
        note = match.group(0).strip()
        notes.append(note.strip("[]"))
        return ""

    cleaned = re.sub(r"\[[^\]]*[\u0C00-\u0C7F][^\]]*\]", replace_note, text or "")
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned, notes


def _prepare_english_translation(record: dict[str, Any]) -> tuple[str, list[str]]:
    text, notes = _remove_telugu_inline_notes(record.get("english_translation") or "")
    return _normalize_english_punctuation(_standardize_english_terms(text)), notes


def _source_records() -> list[dict[str, Any]]:
    settings = get_settings()
    reviewed = read_jsonl(settings.reviewed_pages)
    if reviewed:
        return reviewed
    return read_jsonl(settings.translated_pages)


def _split_long_record(record: dict[str, Any]) -> list[dict[str, Any]]:
    text = record.get("english_translation") or ""
    if word_count_english(text) <= TARGET_MAX_WORDS:
        return [record]

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if len(paragraphs) <= 1:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        paragraphs = [sentence.strip() for sentence in sentences if sentence.strip()]

    parts: list[dict[str, Any]] = []
    current: list[str] = []
    for paragraph in paragraphs:
        candidate = "\n\n".join(current + [paragraph])
        if current and word_count_english(candidate) > TARGET_MAX_WORDS:
            child = dict(record)
            child["english_translation"] = "\n\n".join(current)
            parts.append(child)
            current = [paragraph]
        else:
            current.append(paragraph)
    if current:
        child = dict(record)
        child["english_translation"] = "\n\n".join(current)
        parts.append(child)
    return parts


def _group_key(record: dict[str, Any]) -> tuple[Any, Any]:
    return record.get("kanda"), record.get("chapter_number")


def _build_chunk(records: list[dict[str, Any]], sequence_number: int) -> dict[str, Any]:
    first = records[0]
    last = records[-1]
    english_parts: list[str] = []
    extracted_notes: list[str] = []
    for record in records:
        if not record.get("english_translation"):
            continue
        prepared_text, note_parts = _prepare_english_translation(record)
        if prepared_text:
            english_parts.append(prepared_text.strip())
        extracted_notes.extend(note_parts)
    english_translation = "\n\n".join(english_parts)
    original_telugu = "\n\n".join(
        record.get("original_telugu_cleaned", "").strip() for record in records if record.get("original_telugu_cleaned")
    )
    keywords = unique_ordered(
        keyword
        for record in records
        for keyword in (record.get("keywords") or [])
        if keyword
    )
    entities = merge_entities(records)
    summaries = [record.get("summary", "").strip() for record in records if record.get("summary")]
    notes = [record.get("translation_notes", "").strip() for record in records if record.get("translation_notes")]
    notes.extend(extracted_notes)
    page_numbers = [int(record.get("page_number")) for record in records if record.get("page_number")]
    kanda = first.get("kanda") or "Front Matter"
    chapter_number = first.get("chapter_number")
    if chapter_number is None:
        chapter_number = 0
    chapter_title = first.get("chapter_title") or ("Preface and Table of Contents" if chapter_number == 0 else None)

    chunk = {
        "chunk_id": make_chunk_id(kanda, chapter_number, sequence_number),
        "source_file": first.get("source_file", "ramayana.pdf"),
        "kanda": kanda,
        "chapter_number": chapter_number,
        "chapter_title": chapter_title,
        "sarga_range": first.get("sarga_range"),
        "page_start": min(page_numbers) if page_numbers else None,
        "page_end": max(page_numbers) if page_numbers else None,
        "sequence_number": sequence_number,
        "original_telugu_cleaned": original_telugu,
        "english_translation": english_translation,
        "summary": " ".join(summaries).strip(),
        "keywords": keywords,
        "entities": entities,
        "notes": " ".join(notes).strip(),
        "word_count": word_count_english(english_translation),
        "embedding_text": " ".join(
            part
            for part in [
                first.get("kanda") or "",
                str(first.get("chapter_number") or ""),
                first.get("chapter_title") or "",
                " ".join(keywords),
                english_translation,
            ]
            if part
        ),
    }
    if chunk["chunk_id"].endswith("chunk_000"):
        chunk["chunk_id"] = f"{chunk['chunk_id']}_{stable_hash(english_translation, 6)}"
    return chunk


def chunk_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    expanded: list[dict[str, Any]] = []
    for record in records:
        expanded.extend(_split_long_record(record))

    chunks: list[dict[str, Any]] = []
    sequence = 1
    current: list[dict[str, Any]] = []
    current_key: tuple[Any, Any] | None = None

    for record in expanded:
        key = _group_key(record)
        candidate = current + [record]
        candidate_text = "\n\n".join(item.get("english_translation", "") for item in candidate)
        candidate_words = word_count_english(candidate_text)

        should_flush = False
        if current and key != current_key:
            should_flush = True
        elif current and candidate_words > TARGET_MAX_WORDS:
            should_flush = True

        if should_flush:
            chunks.append(_build_chunk(current, sequence))
            sequence += 1
            current = [record]
            current_key = key
        else:
            current = candidate
            current_key = key

    if current:
        chunks.append(_build_chunk(current, sequence))

    # Ensure uniqueness even if metadata is sparse.
    seen: dict[str, int] = {}
    for chunk in chunks:
        chunk_id = chunk["chunk_id"]
        if chunk_id in seen:
            seen[chunk_id] += 1
            chunk["chunk_id"] = f"{chunk_id}_{seen[chunk_id]}"
        else:
            seen[chunk_id] = 1
    return chunks


def chunk_for_rag() -> list[dict[str, Any]]:
    settings = get_settings()
    logger = setup_logging(settings.logs_dir, "chunk_for_rag")
    records = _source_records()
    if not records:
        raise FileNotFoundError(
            f"Missing translated records. Run --translate first after setting DeepSeek credentials. "
            f"Expected {settings.translated_pages} or {settings.reviewed_pages}."
        )

    chunks = chunk_records(records)
    write_jsonl(settings.chunks_jsonl, chunks)
    write_csv(settings.chunks_csv, chunks)
    settings.chunks_pretty_json.write_text(json.dumps(chunks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    logger.info("Wrote %s chunks to %s", len(chunks), settings.output_dir)
    return chunks


if __name__ == "__main__":
    chunk_for_rag()
