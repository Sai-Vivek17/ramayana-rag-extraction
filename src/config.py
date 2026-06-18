from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - handled by requirements in normal use
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    project_root: Path = PROJECT_ROOT
    data_dir: Path = PROJECT_ROOT / "data"
    raw_dir: Path = PROJECT_ROOT / "data" / "raw"
    extracted_dir: Path = PROJECT_ROOT / "data" / "extracted"
    output_dir: Path = PROJECT_ROOT / "data" / "output"
    glossary_dir: Path = PROJECT_ROOT / "data" / "glossary"
    logs_dir: Path = PROJECT_ROOT / "logs"

    ramayana_pdf: Path = PROJECT_ROOT / "data" / "raw" / "ramayana.pdf"
    assignment_pdf: Path = PROJECT_ROOT / "data" / "raw" / "Ramayana_QA_Assignment.pdf"

    inspection_report: Path = PROJECT_ROOT / "data" / "extracted" / "pdf_inspection_report.json"
    pages_raw: Path = PROJECT_ROOT / "data" / "extracted" / "pages_raw.jsonl"
    pages_cleaned: Path = PROJECT_ROOT / "data" / "extracted" / "pages_cleaned_telugu.jsonl"
    metadata_map: Path = PROJECT_ROOT / "data" / "extracted" / "metadata_map.json"
    translated_pages: Path = PROJECT_ROOT / "data" / "extracted" / "translated_pages.jsonl"
    reviewed_pages: Path = PROJECT_ROOT / "data" / "extracted" / "translated_pages_reviewed.jsonl"

    chunks_jsonl: Path = PROJECT_ROOT / "data" / "output" / "ramayana_rag_chunks.jsonl"
    chunks_csv: Path = PROJECT_ROOT / "data" / "output" / "ramayana_rag_chunks.csv"
    chunks_pretty_json: Path = PROJECT_ROOT / "data" / "output" / "ramayana_rag_chunks_pretty.json"
    validation_report: Path = PROJECT_ROOT / "data" / "output" / "validation_report.json"
    quality_report: Path = PROJECT_ROOT / "data" / "output" / "quality_report.md"

    glossary_terms: Path = PROJECT_ROOT / "data" / "glossary" / "glossary_terms.json"
    transliteration_rules: Path = PROJECT_ROOT / "data" / "glossary" / "transliteration_rules.json"

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    deepseek_temperature: float = 0.2
    deepseek_max_tokens: int = 4096
    enable_review_pass: bool = True
    tesseract_cmd: str = ""

    @classmethod
    def load(cls) -> "Settings":
        env_path = PROJECT_ROOT / ".env"
        if load_dotenv is not None:
            load_dotenv(env_path if env_path.exists() else None, encoding="utf-8-sig")

        return cls(
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", "").strip(),
            deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"),
            deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip(),
            deepseek_temperature=float(os.getenv("DEEPSEEK_TEMPERATURE", "0.2")),
            deepseek_max_tokens=int(os.getenv("DEEPSEEK_MAX_TOKENS", "4096")),
            enable_review_pass=os.getenv("ENABLE_REVIEW_PASS", "true").lower() in {"1", "true", "yes", "on"},
            tesseract_cmd=os.getenv("TESSERACT_CMD", "").strip(),
        )

    def ensure_directories(self) -> None:
        for path in [
            self.raw_dir,
            self.extracted_dir,
            self.output_dir,
            self.glossary_dir,
            self.logs_dir,
        ]:
            path.mkdir(parents=True, exist_ok=True)

    def require_ramayana_pdf(self) -> None:
        if not self.ramayana_pdf.exists():
            raise FileNotFoundError(
                f"Missing source PDF: {self.ramayana_pdf}. "
                "Place ramayana.pdf in data/raw or upload it through the Streamlit app."
            )

    def require_deepseek_key(self) -> None:
        if not self.deepseek_api_key or self.deepseek_api_key == "your_deepseek_api_key_here":
            raise RuntimeError(
                "DeepSeek API key is required for translation/review. "
                "Create .env from .env.example and set DEEPSEEK_API_KEY. "
                "Do not commit .env."
            )


def get_settings() -> Settings:
    settings = Settings.load()
    settings.ensure_directories()
    return settings
