from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import get_settings
from src.utils import read_json, read_jsonl, word_count_english


def paths() -> dict[str, Path]:
    settings = get_settings()
    return {
        "ramayana_pdf": settings.ramayana_pdf,
        "assignment_pdf": settings.assignment_pdf,
        "inspection": settings.inspection_report,
        "pages_raw": settings.pages_raw,
        "pages_cleaned": settings.pages_cleaned,
        "metadata": settings.metadata_map,
        "translated": settings.translated_pages,
        "reviewed": settings.reviewed_pages,
        "chunks_jsonl": settings.chunks_jsonl,
        "chunks_csv": settings.chunks_csv,
        "chunks_pretty_json": settings.chunks_pretty_json,
        "validation": settings.validation_report,
        "quality": settings.quality_report,
    }


def file_status() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for label, path in paths().items():
        result[label] = {
            "exists": path.exists(),
            "path": path,
            "size": path.stat().st_size if path.exists() else 0,
        }
    return result


def pipeline_status() -> dict[str, Any]:
    settings = get_settings()
    inspection = read_json(settings.inspection_report, default={}) or {}
    validation = read_json(settings.validation_report, default={}) or {}
    chunks = read_jsonl(settings.chunks_jsonl)
    translated = read_jsonl(settings.reviewed_pages) or read_jsonl(settings.translated_pages)
    return {
        "total_pages": inspection.get("summary", {}).get("total_pages", 0),
        "ocr_count": inspection.get("summary", {}).get("ocr_recommended_pages", 0),
        "chunk_count": len(chunks),
        "translated_count": len(translated),
        "validation_errors": validation.get("error_count", 0),
        "validation_warnings": validation.get("warning_count", 0),
        "model": settings.deepseek_model,
        "env_key_present": bool(settings.deepseek_api_key and settings.deepseek_api_key != "your_deepseek_api_key_here"),
        "review_enabled": settings.enable_review_pass,
    }


def run_stage(flag: str) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(PROJECT_ROOT / "src" / "run_pipeline.py"), f"--{flag}"]
    return subprocess.run(cmd, cwd=PROJECT_ROOT, text=True, capture_output=True, check=False)


def run_full_pipeline(skip_ocr: bool = False) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(PROJECT_ROOT / "src" / "run_pipeline.py"), "--all"]
    if skip_ocr:
        cmd.append("--skip-ocr")
    return subprocess.run(cmd, cwd=PROJECT_ROOT, text=True, capture_output=True, check=False)


def save_upload(upload, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(upload.getbuffer())


def load_pages() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[int, dict[str, Any]]]:
    settings = get_settings()
    raw = read_jsonl(settings.pages_raw)
    cleaned = read_jsonl(settings.pages_cleaned)
    metadata = read_json(settings.metadata_map, default={}) or {}
    metadata_by_page = {int(page["page_number"]): page for page in metadata.get("pages", [])}
    return raw, cleaned, metadata_by_page


def load_translations() -> list[dict[str, Any]]:
    settings = get_settings()
    return read_jsonl(settings.reviewed_pages) or read_jsonl(settings.translated_pages)


def load_chunks() -> list[dict[str, Any]]:
    settings = get_settings()
    chunks = read_jsonl(settings.chunks_jsonl)
    for chunk in chunks:
        chunk.setdefault("word_count", word_count_english(chunk.get("english_translation", "")))
    return chunks


def search_chunks(chunks: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    query = (query or "").strip().lower()
    if not query:
        return chunks
    results = []
    for chunk in chunks:
        haystack = json.dumps(chunk, ensure_ascii=False).lower()
        if query in haystack:
            results.append(chunk)
    return results

