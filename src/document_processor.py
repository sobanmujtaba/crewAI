"""Read files, classify them, and extract facts and bank transactions with page references."""
import io
import re
from datetime import datetime

from src.models import Fact

DOC_TYPES = ["Loan application", "Pay stub", "W-2", "Tax return", "Bank statement", "Employment verification",
             "Credit report", "Appraisal", "Purchase contract", "Gift letter", "Other"]
KEYS = {  # first match wins
    "Employment verification": ["verification of employment", "employer letter", "employment letter", "reverification", "voe"],
    "Pay stub": ["pay stub", "paystub", "earnings statement"],
    "W-2": ["w-2", "w2"], "Tax return": ["tax return", "1040"],
    "Bank statement": ["bank statement", "bank statements", "account statement", "account statements", "checking", "savings", "statement period"],
    "Credit report": ["credit report", "credit summary", "credit score"], "Appraisal": ["appraisal", "appraised value"],
    "Purchase contract": ["purchase contract", "purchase agreement", "sales contract"],
    "Gift letter": ["gift letter"], "Loan application": ["loan application", "application", "1003"],
}
NUM = r"\D{0,6}?([\d,]+(?:\.\d+)?)"
PATTERNS = [  # field, regex, document types it applies to, numeric?
    ("monthly_income", r"(?:gross\s+)?monthly\s+(?:base\s+)?income" + NUM, {"Loan application", "Pay stub"}, True),
    ("assets_total", r"total\s+assets" + NUM, {"Loan application"}, True),
    ("assets_total", r"(?:ending|closing)\s+balance" + NUM, {"Bank statement"}, True),
    ("property_value", r"(?:estimated\s+)?property\s+value" + NUM, {"Loan application"}, True),
    ("property_value", r"appraised\s+value" + NUM, {"Appraisal"}, True),
    ("loan_amount", r"loan\s+amount" + NUM, {"Loan application"}, True),
    ("purchase_price", r"purchase\s+price" + NUM, {"Loan application", "Purchase contract"}, True),
    ("loan_amount", r"first\s+mortgage" + NUM, {"Purchase contract"}, True),
    ("employer", r"employer(?:\s+name)?\s*:\s*([^.\n]+)", {"Loan application", "Pay stub", "Employment verification"}, False),
    ("borrower_name", r"borrower(?:\s+name)?\s*:\s*([^.\n]+)", {"Loan application"}, False),
]
TX = re.compile(r"^(\d{1,2}/\d{1,2})\s+(.+?)\s+(-?)\$?([\d,]+\.\d{2})\s*$", re.M)
OUTFLOW = re.compile(r"withdraw|payment|purchase|debit|fee|check|transfer to|transfer out", re.I)
TX2 = re.compile(r"(\d{4}-\d{2}-\d{2})\s+([A-Za-z ]+?):\s*\$([\d,]+(?:\.\d{2})?)")


def classify(name, head):
    """Match keywords on the 'Document:' line (if any) and the file name, using whole words."""
    m = re.search(r"^Document:\s*(.+)$", head, re.M)
    s = ((m.group(1) if m else head[:600]) + " " + re.sub(r"[_\-.]+", " ", name)).lower()
    return next((t for t, ks in KEYS.items()
                 if any(re.search(r"\b" + re.escape(k) + r"\b", s) for k in ks)), "Other")


def read_pages(name, data):
    """Return (list of page texts, text_ok). Falls back to OCR for image-only PDF pages."""
    try:
        if name.lower().endswith(".pdf"):
            import fitz  # PyMuPDF
            pages = []
            for pg in fitz.open(stream=data, filetype="pdf"):
                t = pg.get_text()
                if len(t.strip()) < 20:
                    try:  # OCR fallback needs the Tesseract program installed
                        t = pg.get_text(textpage=pg.get_textpage_ocr())
                    except Exception:
                        pass
                pages.append(t)
        elif name.lower().endswith(".docx"):
            from docx import Document
            pages = ["\n".join(p.text for p in Document(io.BytesIO(data)).paragraphs)]
        else:
            pages = [data.decode("utf-8", errors="ignore")]
        return pages, any(len(p.strip()) >= 20 for p in pages)
    except Exception:
        return [], False


def extract_facts(name, doc_type, pages):
    """First match per field, keeping the page it came from."""
    facts = []
    for field, rx, types, numeric in PATTERNS:
        if doc_type not in types:
            continue
        for i, t in enumerate(pages, 1):
            m = re.search(rx, t, re.I)
            if not m:
                continue
            raw = m.group(1).strip()
            try:
                v = float(raw.replace(",", "")) if numeric else raw
            except ValueError:
                continue
            facts.append(Fact(field=field, value=v, document=name, doc_type=doc_type, page=i).model_dump())
            break
    if not any(f["field"] == "monthly_income" for f in facts) and doc_type in (
            "Loan application", "Pay stub", "Employment verification"):
        for i, t in enumerate(pages, 1):
            m = re.search(r"annual\s+(?:base\s+)?salary" + NUM, t, re.I)
            if m:  # annual / 12 = monthly
                v = round(float(m.group(1).replace(",", "")) / 12, 2)
                facts.append(Fact(field="monthly_income", value=v, document=name, doc_type=doc_type,
                                  page=i, confidence=0.85).model_dump())
                break
    return facts


def extract_transactions(name, pages):
    rows = []
    for i, t in enumerate(pages, 1):
        for d, desc, neg, amt in TX.findall(t):
            a = float(amt.replace(",", "")) * (-1 if neg else 1)
            if OUTFLOW.search(desc):
                a = -abs(a)
            rows.append({"document": name, "page": i, "date": d, "desc": desc, "amount": a, "source_doc": None})
        for dte, desc, amt in TX2.findall(t):  # inline ISO-date format
            a = float(amt.replace(",", ""))
            rows.append({"document": name, "page": i, "date": dte, "desc": desc.strip(),
                         "amount": -a if OUTFLOW.search(desc) else a, "source_doc": None})
    return rows


def process_file(name, data):
    """Return (doc record, page texts, facts, transactions). Never invents data on failure."""
    pages, ok = read_pages(name, data)
    dtype = classify(name, "\n".join(pages))
    doc = {"filename": name, "document_type": dtype, "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
           "page_count": len(pages), "processing_status": "Processed" if ok else "Extraction failed - manual review required"}
    facts = extract_facts(name, dtype, pages) if ok else []
    txns = extract_transactions(name, pages) if ok and dtype == "Bank statement" else []
    return doc, pages, facts, txns
