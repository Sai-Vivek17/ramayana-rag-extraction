from __future__ import annotations

from src.validate_output import validate_chunks


def valid_chunk():
    return {
        "chunk_id": "bala_kanda_chapter_001_chunk_001",
        "source_file": "ramayana.pdf",
        "kanda": "Bala Kanda",
        "chapter_number": 1,
        "chapter_title": "First Chapter",
        "sarga_range": "1-6",
        "page_start": 12,
        "page_end": 13,
        "sequence_number": 1,
        "original_telugu_cleaned": "రాముడు అయోధ్యలో జన్మించాడు.",
        "english_translation": "Rama was born in Ayodhya in a sacred royal lineage. " * 8,
        "summary": "Rama is born in Ayodhya.",
        "keywords": ["Rama", "Ayodhya"],
        "entities": {"people": ["Rama"], "places": ["Ayodhya"], "concepts": ["Dharma"]},
        "notes": "",
    }


def test_validation_accepts_required_fields():
    report = validate_chunks([valid_chunk()])

    assert report["error_count"] == 0


def test_validation_rejects_empty_translation():
    chunk = valid_chunk()
    chunk["english_translation"] = ""

    report = validate_chunks([chunk])

    assert report["error_count"] >= 1
    assert any(error["field"] == "english_translation" for error in report["errors"])

