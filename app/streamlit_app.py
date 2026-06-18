from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from app_utils import (
    file_status,
    load_chunks,
    load_pages,
    load_translations,
    pipeline_status,
    paths,
    run_full_pipeline,
    run_stage,
    save_upload,
    search_chunks,
)


st.set_page_config(page_title="Ramayana RAG Extraction", page_icon="R", layout="wide")


def metric_row(status: dict) -> None:
    cols = st.columns(5)
    cols[0].metric("Pages", status["total_pages"])
    cols[1].metric("Translated", status["translated_count"])
    cols[2].metric("Chunks", status["chunk_count"])
    cols[3].metric("OCR Flags", status["ocr_count"])
    cols[4].metric("Validation", f"{status['validation_errors']} errors / {status['validation_warnings']} warnings")


def show_output(result) -> None:
    if result.returncode == 0:
        st.success("Stage completed.")
    else:
        st.error(f"Stage failed with exit code {result.returncode}.")
    if result.stdout:
        st.code(result.stdout, language="text")
    if result.stderr:
        st.code(result.stderr, language="text")


def home_page() -> None:
    st.title("Ramayana Source Extraction, Translation & Structuring for RAG")
    st.caption("DeepSeek-only translation pipeline with local extraction, review, validation, and export.")
    status = pipeline_status()
    metric_row(status)
    st.divider()

    rows = []
    for label, item in file_status().items():
        rows.append({"artifact": label, "exists": item["exists"], "size_bytes": item["size"], "path": str(item["path"])})
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


def file_setup_page() -> None:
    st.header("File Setup")
    current_paths = paths()
    cols = st.columns(2)
    with cols[0]:
        upload = st.file_uploader("ramayana.pdf", type=["pdf"], key="ramayana_upload")
        if upload and st.button("Save ramayana.pdf"):
            save_upload(upload, current_paths["ramayana_pdf"])
            st.success("Saved ramayana.pdf.")
    with cols[1]:
        upload = st.file_uploader("Ramayana_QA_Assignment.pdf", type=["pdf"], key="assignment_upload")
        if upload and st.button("Save assignment PDF"):
            save_upload(upload, current_paths["assignment_pdf"])
            st.success("Saved assignment PDF.")
    st.divider()
    rows = []
    for key in ["ramayana_pdf", "assignment_pdf"]:
        item = file_status()[key]
        rows.append({"file": key, "present": item["exists"], "size_bytes": item["size"], "path": str(item["path"])})
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


def pipeline_runner_page() -> None:
    st.header("Pipeline Runner")
    st.warning("Translation and review call DeepSeek and may use API credits. The API key is read from `.env` and is never displayed.")
    stage_labels = [
        ("inspect", "Inspect PDF"),
        ("extract", "Extract Text"),
        ("ocr", "OCR Fallback"),
        ("clean", "Clean Telugu"),
        ("metadata", "Detect Metadata"),
        ("translate", "Translate using DeepSeek"),
        ("review", "Review Translation"),
        ("chunk", "Chunk for RAG"),
        ("validate", "Validate"),
        ("report", "Generate Report"),
    ]
    cols = st.columns(3)
    for index, (flag, label) in enumerate(stage_labels):
        with cols[index % 3]:
            if st.button(label, use_container_width=True):
                show_output(run_stage(flag))

    st.divider()
    skip_ocr = st.checkbox("Skip OCR during full pipeline", value=False)
    if st.button("Run Full Pipeline", type="primary"):
        show_output(run_full_pipeline(skip_ocr=skip_ocr))


def page_inspection_viewer() -> None:
    st.header("Page Inspection Viewer")
    raw, cleaned, metadata = load_pages()
    if not raw:
        st.info("Run extraction first.")
        return
    pages = [record["page_number"] for record in raw]
    page_number = st.selectbox("Page", pages)
    raw_record = next((record for record in raw if record["page_number"] == page_number), {})
    clean_record = next((record for record in cleaned if record["page_number"] == page_number), {})
    meta = metadata.get(int(page_number), {})

    cols = st.columns(4)
    cols[0].metric("Method", raw_record.get("extraction_method", ""))
    cols[1].metric("Needs OCR", str(raw_record.get("needs_ocr", "")))
    cols[2].metric("Telugu Ratio", raw_record.get("telugu_ratio", 0))
    cols[3].metric("Clean Chars", clean_record.get("cleaned_char_count", 0))

    left, right = st.columns(2)
    with left:
        st.subheader("Raw Text")
        st.text_area("Raw", raw_record.get("raw_text", ""), height=380, label_visibility="collapsed")
    with right:
        st.subheader("Cleaned Telugu")
        st.text_area("Cleaned", clean_record.get("cleaned_text", ""), height=380, label_visibility="collapsed")
    st.subheader("Metadata")
    st.json(meta)


def translation_review_page() -> None:
    st.header("Translation Review")
    translations = load_translations()
    if not translations:
        st.info("Run translation first.")
        return
    page_numbers = [record.get("page_number") for record in translations]
    selected = st.selectbox("Page", page_numbers)
    record = next((item for item in translations if item.get("page_number") == selected), {})

    left, right = st.columns(2)
    with left:
        st.subheader("Telugu Source")
        st.text_area("Telugu", record.get("original_telugu_cleaned", ""), height=420, label_visibility="collapsed")
    with right:
        st.subheader("English Translation")
        st.text_area("English", record.get("english_translation", ""), height=420, label_visibility="collapsed")

    cols = st.columns(3)
    with cols[0]:
        st.subheader("Summary")
        st.write(record.get("summary", ""))
    with cols[1]:
        st.subheader("Keywords")
        st.write(", ".join(record.get("keywords") or []))
    with cols[2]:
        st.subheader("Entities")
        st.json(record.get("entities") or {})
    st.subheader("Notes")
    st.write(record.get("translation_notes") or record.get("review", {}).get("review_notes") or "")

    if st.button("Mark Page Reviewed"):
        flags_path = Path("data/extracted/manual_review_flags.json")
        flags_path.parent.mkdir(parents=True, exist_ok=True)
        existing = json.loads(flags_path.read_text(encoding="utf-8")) if flags_path.exists() else {}
        existing[str(selected)] = {"manual_reviewed": True}
        flags_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        st.success("Marked as manually reviewed.")


def chunk_explorer_page() -> None:
    st.header("Chunk Explorer")
    chunks = load_chunks()
    if not chunks:
        st.info("Run chunking first.")
        return
    query = st.text_input("Search")
    kandas = sorted({chunk.get("kanda") for chunk in chunks if chunk.get("kanda")})
    kanda = st.selectbox("Kanda", ["All"] + kandas)
    filtered = search_chunks(chunks, query)
    if kanda != "All":
        filtered = [chunk for chunk in filtered if chunk.get("kanda") == kanda]
    chapters = sorted({chunk.get("chapter_number") for chunk in filtered if chunk.get("chapter_number")})
    chapter = st.selectbox("Chapter", ["All"] + chapters)
    if chapter != "All":
        filtered = [chunk for chunk in filtered if chunk.get("chapter_number") == chapter]

    st.caption(f"{len(filtered)} chunks")
    ids = [chunk["chunk_id"] for chunk in filtered]
    selected = st.selectbox("Chunk", ids) if ids else None
    if not selected:
        return
    chunk = next(item for item in filtered if item["chunk_id"] == selected)
    cols = st.columns(4)
    cols[0].metric("Words", chunk.get("word_count", 0))
    cols[1].metric("Page Start", chunk.get("page_start"))
    cols[2].metric("Page End", chunk.get("page_end"))
    cols[3].metric("Sequence", chunk.get("sequence_number"))
    st.subheader("English Translation")
    st.write(chunk.get("english_translation", ""))
    st.subheader("Metadata")
    st.json({key: chunk.get(key) for key in ["kanda", "chapter_number", "chapter_title", "sarga_range", "keywords", "entities"]})
    st.download_button(
        "Download Selected Chunk",
        data=json.dumps(chunk, ensure_ascii=False, indent=2),
        file_name=f"{chunk['chunk_id']}.json",
        mime="application/json",
    )


def downloads_page() -> None:
    st.header("Output Downloads")
    for label, path in paths().items():
        if label not in {"chunks_jsonl", "chunks_csv", "chunks_pretty_json", "validation", "quality"}:
            continue
        if path.exists():
            mime = "text/markdown" if path.suffix == ".md" else "text/csv" if path.suffix == ".csv" else "application/json"
            st.download_button(label, data=path.read_bytes(), file_name=path.name, mime=mime)
        else:
            st.caption(f"{label}: not available")


def quality_report_page() -> None:
    st.header("Quality Report")
    quality = paths()["quality"]
    validation = paths()["validation"]
    if quality.exists():
        st.markdown(quality.read_text(encoding="utf-8"))
    else:
        st.info("Generate the quality report first.")
    if validation.exists():
        with st.expander("Validation JSON"):
            st.json(json.loads(validation.read_text(encoding="utf-8")))


def settings_page() -> None:
    st.header("Settings")
    status = pipeline_status()
    rows = [
        {"setting": "DeepSeek key present", "value": "yes" if status["env_key_present"] else "no"},
        {"setting": "DeepSeek model", "value": status["model"]},
        {"setting": "Review pass enabled", "value": status["review_enabled"]},
    ]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.code(
        "copy .env.example .env\n"
        "notepad .env\n"
        "python src/run_pipeline.py --translate --review --chunk --validate --report",
        language="powershell",
    )
    st.caption("The API key is loaded from `.env` and is not printed, stored in outputs, or shown in this app.")


PAGES = {
    "Dashboard": home_page,
    "File Setup": file_setup_page,
    "Pipeline Runner": pipeline_runner_page,
    "Page Viewer": page_inspection_viewer,
    "Translation Review": translation_review_page,
    "Chunk Explorer": chunk_explorer_page,
    "Downloads": downloads_page,
    "Quality Report": quality_report_page,
    "Settings": settings_page,
}


choice = st.sidebar.radio("View", list(PAGES))
PAGES[choice]()
