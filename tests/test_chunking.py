from __future__ import annotations

from src.chunk_for_rag import chunk_records, make_chunk_id


def test_chunk_id_is_stable():
    assert make_chunk_id("Bala Kanda", 1, 3) == "bala_kanda_chapter_001_chunk_003"


def test_chunking_keeps_short_record_as_one_chunk():
    records = [
        {
            "page_number": 12,
            "source_file": "ramayana.pdf",
            "kanda": "Bala Kanda",
            "chapter_number": 1,
            "chapter_title": "First Chapter",
            "sarga_range": "1-6",
            "original_telugu_cleaned": "రాముడు",
            "english_translation": "Rama is introduced in a dignified devotional context.",
            "summary": "Rama is introduced.",
            "keywords": ["Rama"],
            "entities": {"people": ["Rama"], "places": [], "concepts": []},
            "translation_notes": "",
        }
    ]

    chunks = chunk_records(records)

    assert len(chunks) == 1
    assert chunks[0]["chunk_id"] == "bala_kanda_chapter_001_chunk_001"
    assert chunks[0]["page_start"] == 12
    assert chunks[0]["page_end"] == 12

