# Ramayana Source Extraction, Translation & Structuring for RAG

Completed assignment repository for extracting Telugu Ramayana source text, translating it with DeepSeek, reviewing it, and exporting clean English RAG-ready chunks.

## Final Deliverable Status

- Source PDF pages inspected: `248`
- Telugu pages translated with DeepSeek: `247`
- DeepSeek-reviewed translated records: `247`
- Final RAG chunks: `181`
- Validation errors: `0`
- Validation warnings: `0`
- Streamlit website: included and tested locally

Page 1 of `ramayana.pdf` contains font-encoded/private-use glyph noise. Tesseract OCR was attempted but Tesseract was not installed on the local machine, so that page was skipped instead of sending unusable glyph text to DeepSeek. The remaining 247 Telugu pages were translated and reviewed.

## Assignment Constraint

DeepSeek is the only model used for Ramayana content translation, review, summarization, keyword generation, and entity extraction. No OpenAI/GPT, Gemini, Claude, or other LLM API is used for content generation.

The code uses normal Python libraries for PDF extraction, OCR fallback, cleaning, validation, reporting, and the Streamlit interface.

## What Was Added Beyond the Initial Brief

In addition to the required extraction/translation/chunking pipeline, this repository includes:

- A polished Streamlit website for setup, pipeline execution, page inspection, translation review, chunk search, downloads, quality report viewing, and settings.
- Resume-safe DeepSeek translation and review stages.
- DeepSeek-only JSON repair fallback for malformed model JSON.
- Fail-soft review handling so one bad review response does not block the whole pipeline.
- Glossary-guided translation prompts and final glossary consistency validation.
- Final ASCII-normalized English chunk text for cleaner downstream ingestion.
- Validation reports with zero final errors/warnings.
- A sample notebook for quick output inspection.

## Streamlit Website

Run the app:

```powershell
streamlit run app/streamlit_app.py
```

During local verification, the app was served successfully at:

```text
http://localhost:8507
```

The app includes:

- Dashboard with pipeline status cards
- File setup and PDF upload page
- Pipeline runner buttons
- Raw/cleaned page inspection viewer
- Telugu/English translation review page
- Chunk explorer with search and filters
- Output download page
- Quality report page
- Safe settings page that never reveals the API key

Optional screenshot capture command, after the app is running:

```powershell
New-Item -ItemType Directory -Force -Path docs\screenshots
```

Then capture the page using any browser screenshot tool and save it as:

```text
docs/screenshots/streamlit-dashboard.png
```

If added, reference it in this README with:

```markdown
![Streamlit dashboard](docs/screenshots/streamlit-dashboard.png)
```

## Repository Structure

```text
ramayana-rag-extraction/
  README.md
  .gitignore
  requirements.txt
  .env.example
  data/
    raw/
      ramayana.pdf
      Ramayana_QA_Assignment.pdf
    extracted/
      pdf_inspection_report.json
      pages_raw.jsonl
      pages_cleaned_telugu.jsonl
      metadata_map.json
      translated_pages.jsonl
      translated_pages_reviewed.jsonl
    output/
      ramayana_rag_chunks.jsonl
      ramayana_rag_chunks.csv
      ramayana_rag_chunks_pretty.json
      validation_report.json
      quality_report.md
    glossary/
      glossary_terms.json
      transliteration_rules.json
  src/
  app/
  notebooks/
  tests/
```

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Create a local `.env` file from the template:

```powershell
copy .env.example .env
notepad .env
```

Set your key safely:

```text
DEEPSEEK_API_KEY=your_real_deepseek_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TEMPERATURE=0.2
DEEPSEEK_MAX_TOKENS=4096
ENABLE_REVIEW_PASS=true
```

Never commit `.env`.

## Tesseract OCR Setup

OCR fallback is supported for weak/scanned pages.

1. Install Tesseract OCR for Windows.
2. Install Telugu traineddata (`tel.traineddata`) into the Tesseract `tessdata` folder.
3. Add Tesseract to PATH or set:

```text
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

## Run the Pipeline

Run everything:

```powershell
python src/run_pipeline.py --all
```

Run local preprocessing only:

```powershell
python src/run_pipeline.py --inspect --extract --ocr --clean --metadata --report
```

Run DeepSeek and final output stages:

```powershell
python src/run_pipeline.py --translate --review --chunk --validate --report
```

Run final deterministic stages again:

```powershell
python src/run_pipeline.py --chunk --validate --report
```

## Output Files

Final RAG-ready outputs are in `data/output/`:

- `ramayana_rag_chunks.jsonl` - primary RAG ingestion file
- `ramayana_rag_chunks.csv` - spreadsheet-friendly output
- `ramayana_rag_chunks_pretty.json` - readable JSON export
- `validation_report.json` - final validation result
- `quality_report.md` - human-readable quality summary

Intermediate extracted and translated material is in `data/extracted/`:

- `pages_raw.jsonl`
- `pages_cleaned_telugu.jsonl`
- `metadata_map.json`
- `translated_pages.jsonl`
- `translated_pages_reviewed.jsonl`

## Final Chunk Schema

```json
{
  "chunk_id": "bala_kanda_chapter_001_chunk_003",
  "source_file": "ramayana.pdf",
  "kanda": "Bala Kanda",
  "chapter_number": 1,
  "chapter_title": "First Chapter",
  "sarga_range": "1-6",
  "page_start": 12,
  "page_end": 13,
  "sequence_number": 3,
  "original_telugu_cleaned": "...",
  "english_translation": "...",
  "summary": "...",
  "keywords": ["Rama", "Dasharatha", "Ayodhya"],
  "entities": {
    "people": ["Rama", "Dasharatha"],
    "places": ["Ayodhya"],
    "concepts": ["Dharma", "Yajna"]
  },
  "notes": "...",
  "word_count": 420,
  "embedding_text": "..."
}
```

`embedding_text` is vector-ready local text. The pipeline does not call any embedding API.

## Validation

Run:

```powershell
python src/run_pipeline.py --validate
```

Validation checks:

- JSONL readability
- Required fields
- Empty Telugu source
- Empty English translation
- Missing metadata
- Bad page ranges
- Broken sequence numbers
- Duplicate chunk IDs
- Telugu characters leaking into English text
- Empty keywords/entities
- Glossary consistency
- Chunk size warnings

Final validation result:

```text
0 errors, 0 warnings, 181 chunks
```

## Tests

```powershell
pytest
```

Final local test result:

```text
7 passed
```

## Security

- `.env` is ignored and must not be committed.
- `.env.example` contains only placeholders.
- Logs are ignored.
- API keys are read from environment variables only.
- No secrets are present in committed output files.

  Streamlit App Interphase:
<img width="1914" height="1076" alt="Screenshot 2026-06-18 204247" src="https://github.com/user-attachments/assets/e870a3c2-d1ec-4d81-a1c8-d3cb4846af6a" />
<img width="1919" height="1071" alt="Screenshot 2026-06-18 204328" src="https://github.com/user-attachments/assets/efb7ccd2-7d7b-4447-bc41-6e75eddef322" />
