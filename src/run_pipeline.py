from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.chunk_for_rag import chunk_for_rag
from src.clean_telugu_text import clean_pages
from src.extract_pdf import extract_pdf_text
from src.generate_quality_report import generate_quality_report
from src.inspect_pdf import inspect_pdf
from src.metadata_detection import build_metadata_map
from src.ocr_fallback import run_ocr_fallback
from src.review_translation_with_deepseek import review_translations
from src.translate_with_deepseek import translate_pages
from src.validate_output import validate_output


STAGE_ORDER = ["inspect", "extract", "ocr", "clean", "metadata", "translate", "review", "chunk", "validate", "report"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Ramayana RAG extraction pipeline.")
    for stage in STAGE_ORDER:
        parser.add_argument(f"--{stage}", action="store_true", help=f"Run {stage} stage")
    parser.add_argument("--all", action="store_true", help="Run all stages in order")
    parser.add_argument("--skip-ocr", action="store_true", help="Skip OCR during --all")
    parser.add_argument("--translation-limit", type=int, default=None, help="Translate only N records for testing")
    parser.add_argument("--review-limit", type=int, default=None, help="Review only N records for testing")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    selected = STAGE_ORDER if args.all else [stage for stage in STAGE_ORDER if getattr(args, stage)]
    if args.all and args.skip_ocr:
        selected = [stage for stage in selected if stage != "ocr"]
    if not selected:
        print("No stages selected. Use --all or one or more stage flags.")
        return 2

    for stage in selected:
        print(f"\n=== {stage.upper()} ===")
        if stage == "inspect":
            inspect_pdf()
        elif stage == "extract":
            extract_pdf_text()
        elif stage == "ocr":
            run_ocr_fallback()
        elif stage == "clean":
            clean_pages()
        elif stage == "metadata":
            build_metadata_map()
        elif stage == "translate":
            translate_pages(limit=args.translation_limit)
        elif stage == "review":
            review_translations(limit=args.review_limit)
        elif stage == "chunk":
            chunk_for_rag()
        elif stage == "validate":
            validate_output()
        elif stage == "report":
            generate_quality_report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

