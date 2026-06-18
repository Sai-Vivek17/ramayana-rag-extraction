from __future__ import annotations

from src.utils import read_jsonl, write_jsonl


def test_jsonl_read_write_round_trip(tmp_path):
    path = tmp_path / "records.jsonl"
    records = [
        {"page_number": 1, "text": "రాముడు"},
        {"page_number": 2, "text": "Sita"},
    ]

    write_jsonl(path, records)

    assert read_jsonl(path) == records

