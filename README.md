# CrewAI: AI Mortgage Underwriting Assistant

A Streamlit copilot for a human mortgage underwriter. It reads loan documents, runs the math in plain Python, finds what does not line up, retrieves relevant guideline text, and drafts conditions. **The AI assists. The underwriter makes the final decision.**

All demo and sample data in this repository is **fictional**.

## What it does

- Extracts fields from PDF, DOCX and TXT files with page-level sources
- Classifies documents and checks completeness (Complete, Missing, Outdated, Review Required, Not Applicable)
- Calculates DTI, LTV, funds to close and reserves in code, never with the LLM
- Compares values across documents (income, employer, assets, property value) without choosing a winner
- Flags large non-payroll deposits and matches own-account transfers
- Searches local guidelines and separates source text from AI interpretation
- Produces a structured AI analysis (Groq) that is validated with Pydantic
- Manages conditions, resubmission comparison, an audit trail and the human decision
- Runs without an API key (demo loan, calculations, discrepancies, guideline search)

## Project structure

```text
app.py                      Streamlit UI (9 pages)
src/
  document_processor.py     File reading, classification, field and transaction extraction
  calculations.py           DTI, LTV, payment, funds to close, reserves
  discrepancy_engine.py     Checklist, cross-document comparison, large deposits
  guideline_rag.py          Guideline chunking and retrieval (TF-IDF, optional FAISS)
  underwriting.py           Findings, suggested conditions, AI context
  llm.py                    Groq client and structured output
  database.py               SQLite audit log, conditions, decisions
  models.py                 Pydantic schemas
  demo.py                   Fictional demo loan
data/
  guidelines/               Guideline files (.txt or .md)
  files/                    Fictional sample borrower documents for testing
tests/                      Unit tests
```

## Setup

### 1. Clone the repository
```bash
git clone [https://github.com/sobanmujtaba/crewAI.git](https://github.com/sobanmujtaba/crewAI.git)
cd crewAI

2. Create a virtual environment (Python 3.11 or newer)
```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

3. Install requirements
```bash
pip install -r requirements.txt
```

4. Configure environment variables
```bash
cp .env.example .env
```
Edit `.env`:
```text
GROQ_API_KEY=gsk_your_key_here
GROQ_MODEL=openai/gpt-oss-120b
```
Get a key at https://console.groq.com. Never commit `.env`.

5. Run
```bash
streamlit run app.py
```

6. Test
```bash
pytest
```

## How to use

1. Start with the **Demo loan** in the sidebar to see the full workflow.
2. To use your own files, switch to **Uploaded loan**, open **Documents**, upload files, then click **Process documents**.
3. Open **Borrower** and enter monthly debt, which is not extracted automatically.
4. Review **Discrepancies**, **Guidelines** and **AI Underwriting**.
5. Accept or edit **Conditions**, then record the **Underwriter Decision**.

Sample borrower files are in `data/files/`.

## Optional settings

| Variable | Purpose |
|---|---|
| `GROQ_MODEL` | Model ID. Default `openai/gpt-oss-120b` |
| `USE_EMBEDDINGS=1` | Use FAISS and sentence-transformers instead of TF-IDF (needs `pip install sentence-transformers faiss-cpu`) |

Large deposit threshold, closing cost percentage and interest rate are editable in the app sidebar under Settings.

## Deploy to Streamlit Community Cloud

1. Push the repo to GitHub. Keep `.env` and `data/*.db` out of Git (see `.gitignore`).
2. Go to https://share.streamlit.io, choose **New app**, select the repo and set the main file to `app.py`.
3. Open **App settings > Secrets** and add:
```toml
GROQ_API_KEY = "gsk_your_key_here"
GROQ_MODEL = "openai/gpt-oss-120b"
```
4. Deploy. `packages.txt` installs Tesseract for OCR on scanned PDFs.

The SQLite file resets when the cloud app restarts, so treat it as prototype storage.

## Limitations

- Extraction uses pattern matching, so unusual document layouts may be missed. Unreadable documents are flagged for manual review, never guessed.
- Guidelines in this repository are a fictional demonstration set. Add your own permitted guideline files to `data/guidelines/`.
- Financial Analysis uses the first bank statement's ending balance as verified assets.
- This is a prototype. It is not a lending decision system and must not be used for real loan decisions without full review.

## License

Add a license of your choice (for example MIT) before publishing.