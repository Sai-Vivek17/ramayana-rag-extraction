from __future__ import annotations

import csv
import hashlib
import json
import logging
import re
import tempfile
import unicodedata
from pathlib import Path
from typing import Any, Iterable

TELUGU_RANGE_RE = re.compile(r"[\u0C00-\u0C7F]")
ASCII_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?")


def setup_logging(logs_dir: Path, name: str = "ramayana_pipeline") -> logging.Logger:
    logs_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(logs_dir / f"{name}.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def normalize_text(text: str) -> str:
    return unicodedata.normalize("NFC", text or "")


def telugu_char_count(text: str) -> int:
    return len(TELUGU_RANGE_RE.findall(text or ""))


def telugu_ratio(text: str) -> float:
    text = text or ""
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return 0.0
    return telugu_char_count(text) / len(letters)


def has_telugu(text: str) -> bool:
    return bool(TELUGU_RANGE_RE.search(text or ""))


def word_count_english(text: str) -> int:
    return len(ASCII_WORD_RE.findall(text or ""))


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent) as tmp:
        tmp.write(text)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def atomic_write_json(path: Path, payload: Any) -> None:
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
    return records


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    lines = [json.dumps(record, ensure_ascii=False, sort_keys=False) for record in records]
    atomic_write_text(path, "\n".join(lines) + ("\n" if lines else ""))


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=False) + "\n")


def write_csv(path: Path, records: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not fieldnames:
        keys: list[str] = []
        for record in records:
            for key in record:
                if key not in keys:
                    keys.append(key)
        fieldnames = keys

    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            row = {}
            for key in fieldnames:
                value = record.get(key)
                if isinstance(value, (dict, list)):
                    row[key] = json.dumps(value, ensure_ascii=False)
                else:
                    row[key] = value
            writer.writerow(row)


def stable_slug(value: str, fallback: str = "item") -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or fallback


def stable_hash(value: str, length: int = 10) -> str:
    return hashlib.sha1((value or "").encode("utf-8")).hexdigest()[:length]


def flatten_entities(entities: dict[str, Any] | None) -> list[str]:
    if not entities:
        return []
    found: list[str] = []
    for value in entities.values():
        if isinstance(value, list):
            found.extend(str(item) for item in value if item)
        elif value:
            found.append(str(value))
    return sorted(set(found))


def unique_ordered(values: Iterable[Any]) -> list[Any]:
    seen: set[str] = set()
    result: list[Any] = []
    for value in values:
        key = json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def merge_entities(records: Iterable[dict[str, Any]]) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {"people": [], "places": [], "concepts": []}
    for record in records:
        entities = record.get("entities") or {}
        if not isinstance(entities, dict):
            continue
        for key in merged:
            values = entities.get(key) or []
            if isinstance(values, str):
                values = [values]
            merged[key].extend(str(value) for value in values if value)
    return {key: unique_ordered(values) for key, values in merged.items()}


def safe_preview(text: str, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."

