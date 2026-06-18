from __future__ import annotations

from statistics import mean
from typing import Any

from src.config import get_settings
from src.glossary import load_glossary
from src.utils import read_json, read_jsonl, safe_preview, setup_logging, word_count_english


def _count(records: list[Any]) -> int:
    return len(records or [])


def generate_quality_report() -> str:
    settings = get_settings()
    logger = setup_logging(settings.logs_dir, "generate_quality_report")

    inspection = read_json(settings.inspection_report, default={}) or {}
    raw_pages = read_jsonl(settings.pages_raw)
    cleaned_pages = read_jsonl(settings.pages_cleaned)
    translated = read_jsonl(settings.reviewed_pages) or read_jsonl(settings.translated_pages)
    chunks = read_jsonl(settings.chunks_jsonl)
    validation = read_json(settings.validation_report, default={}) or {}
    glossary = load_glossary()

    word_counts = [int(chunk.get("word_count") or word_count_english(chunk.get("english_translation", ""))) for chunk in chunks]
    inspection_summary = inspection.get("summary", {})
    sample_chunks = chunks[:3]

    lines = [
        "# Ramayana RAG Extraction Quality Report",
        "",
        "## Processing Summary",
        "",
        f"- Total pages in PDF: {inspection_summary.get('total_pages', 'not inspected')}",
        f"- Extracted page records: {_count(raw_pages)}",
        f"- Cleaned page records: {_count(cleaned_pages)}",
        f"- Text-based pages: {inspection_summary.get('text_based_pages', 'unknown')}",
        f"- Mixed pages: {inspection_summary.get('mixed_pages', 'unknown')}",
        f"- Scanned pages: {inspection_summary.get('scanned_pages', 'unknown')}",
        f"- Garbled/weak pages: {inspection_summary.get('garbled_or_weak_pages', 'unknown')}",
        f"- OCR recommended pages: {inspection_summary.get('ocr_recommended_pages', 'unknown')}",
        f"- Translated records: {_count(translated)}",
        f"- Final chunks: {_count(chunks)}",
        "",
        "## Chunk Statistics",
        "",
        f"- Average chunk word count: {round(mean(word_counts), 1) if word_counts else 0}",
        f"- Minimum chunk word count: {min(word_counts) if word_counts else 0}",
        f"- Maximum chunk word count: {max(word_counts) if word_counts else 0}",
        "",
        "## Validation Summary",
        "",
        f"- Validation errors: {validation.get('error_count', 'not run')}",
        f"- Validation warnings: {validation.get('warning_count', 'not run')}",
        f"- Validation status: {'PASS' if validation.get('ok') else 'REVIEW NEEDED'}",
        "",
        "## DeepSeek Configuration",
        "",
        f"- Model: {settings.deepseek_model}",
        f"- Review pass enabled: {settings.enable_review_pass}",
        f"- Glossary entries: {len(glossary)}",
        "",
        "## Sample Chunks",
        "",
    ]

    if sample_chunks:
        for chunk in sample_chunks:
            lines.extend(
                [
                    f"### {chunk.get('chunk_id')}",
                    "",
                    f"- Kanda: {chunk.get('kanda')}",
                    f"- Chapter: {chunk.get('chapter_number')}",
                    f"- Pages: {chunk.get('page_start')} - {chunk.get('page_end')}",
                    f"- Keywords: {', '.join(chunk.get('keywords') or [])}",
                    "",
                    safe_preview(chunk.get("english_translation", ""), 700),
                    "",
                ]
            )
    else:
        lines.extend(
            [
                "No translated chunks are available yet. This is expected until `.env` contains a valid",
                "`DEEPSEEK_API_KEY` and `python src/run_pipeline.py --translate --review --chunk --validate --report`",
                "has been run.",
                "",
            ]
        )

    lines.extend(
        [
            "## Known Limitations",
            "",
            "- Metadata detection is semi-automatic and should be reviewed in `data/extracted/metadata_map.json`.",
            "- OCR quality depends on local Tesseract installation and Telugu traineddata.",
            "- Translation and review are intentionally DeepSeek-gated; no final Ramayana translation is fabricated without the API call.",
            "- Ambiguous OCR text should remain marked in notes instead of being guessed.",
            "",
            "## Security",
            "",
            "- `.env` is ignored and must never be committed.",
            "- API keys are read from environment variables only.",
            "- Logs are ignored and should be reviewed before sharing if they are manually included.",
        ]
    )

    report = "\n".join(lines) + "\n"
    settings.quality_report.write_text(report, encoding="utf-8")
    logger.info("Wrote quality report to %s", settings.quality_report)
    return report


if __name__ == "__main__":
    generate_quality_report()

