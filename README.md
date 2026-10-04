# CrewAI: AI Mortgage Underwriting Assistant

A Streamlit copilot for a human mortgage underwriter. It reads loan documents, runs the maths in plain
Python, finds discrepancies and large deposits, retrieves guideline text, and drafts conditions.
**The AI assists. The underwriter makes the final decision.** All demo data is fictional.

## Features
- Upload PDF, DOCX or TXT documents, auto-classify them, extract values with page references
- OCR fallback for scanned PDFs, and a clear "manual review required" message when extraction fails
- DTI, LTV, funds to close and reserves calculated in code, with inputs and sources shown
- Document checklist: Complete, Missing, Outdated, Review Required, Not Applicable
- Cross-document discrepancy detection (income, employer, assets, property value)
- Large deposit detection with a configurable threshold, and own-account transfer matching
- Local guideline search (TF-IDF by default, FAISS embeddings optional)
- AI underwriting analysis through Groq, validated with Pydantic
- Evidence viewer, conditions management, resubmission comparison, decision panel, SQLite audit trail
- Built-in fictional demo loan with four deliberate issues, no API key needed

## Workflow
Document > Evidence > Calculation > Guideline > Finding > Condition > Human decision

## Quick start
```bash
git clone <your-repo-url> && cd <your-repo>
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env
streamlit run app.py
```
Open http://localhost:8501. Without an API key everything works except the AI analysis page.

## Configuration
Set these in `.env`:
```
GROQ_API_KEY=gsk_...
GROQ_MODEL=openai/gpt-oss-120b
```
Optional: `USE_EMBEDDINGS=1` turns on FAISS + sentence-transformers search (needs
`pip install sentence-transformers faiss-cpu`, first run downloads a model).
For OCR, install the Tesseract program (`packages.txt` does this on Streamlit Cloud).

## Deploy to Streamlit Community Cloud
1. Push the repo to GitHub. `.env` is git-ignored, never commit keys.
2. At share.streamlit.io choose New app, select the repo, main file `app.py`.
3. Open Settings > Secrets and paste:
```toml
GROQ_API_KEY = "gsk_..."
GROQ_MODEL = "openai/gpt-oss-120b"
```
The SQLite file resets when the cloud app restarts, so treat it as prototype storage.

## Using your own loan files
1. Sidebar: set Loan file to **Uploaded loan**.
2. Documents page: upload files, click **Process documents**.
3. Borrower page: enter monthly debt (not extracted automatically).

## Project structure
```
app.py                     Streamlit UI (all pages)
src/document_processor.py  read, classify, extract facts and transactions
src/calculations.py        DTI, LTV, funds to close, reserves
src/discrepancy_engine.py  checklist, discrepancies, large deposits
src/guideline_rag.py       guideline chunking and search
src/underwriting.py        findings, suggested conditions, AI context
src/llm.py                 Groq access (only file that knows the provider)
src/database.py            SQLite audit, conditions, decisions
src/models.py              Pydantic schemas
src/demo.py                fictional demo loan
data/guidelines/           guideline text (.txt or .md)
tests/                     pytest suite
```
Run tests with `pytest`.

## Limitations
- Extraction uses regex patterns, so unusual document layouts need new patterns
- Monthly debt and multi-statement asset totals are not calculated automatically
- Guidelines are a fictional demo set, not real lending rules. Verify against official sources
- Not a lending decision system. Prototype for demonstration and education only