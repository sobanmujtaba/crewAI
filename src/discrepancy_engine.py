"""Rule-based checks: checklist, cross-document discrepancies, large deposits."""
import difflib
import itertools
import re

ALL_TYPES = ["Loan application", "Pay stub", "W-2", "Tax return", "Bank statement",
             "Employment verification", "Credit report", "Appraisal", "Purchase contract", "Gift letter"]
_BASE = ["Loan application", "Pay stub", "W-2", "Bank statement", "Employment verification",
         "Credit report", "Appraisal", "Purchase contract"]
REQUIRED = {"Conventional 30-Year Fixed": _BASE,
            "Self-Employed Conventional": _BASE + ["Tax return"]}


def checklist(docs, programme):
    """Distinguish a missing document from one that exists but is unreliable."""
    req = REQUIRED.get(programme, _BASE)
    rows = []
    for t in ALL_TYPES:
        found = [d for d in docs if d["document_type"] == t]
        src = ", ".join(d["filename"] for d in found) or "-"
        if found and any("failed" in d["processing_status"] for d in found):
            s, n = "Review Required", "Document exists but could not be reliably read"
        elif found and all(d.get("stale") for d in found):
            s, n = "Outdated", "Document is older than allowed"
        elif found:
            s, n = "Complete", ""
        elif t in req:
            s, n = "Missing", "No document of this type in the file"
        else:
            s, n = "Not Applicable", "Not required for this programme"
        rows.append({"Document": t, "Status": s, "Source": src, "Note": n})
    return rows


def fact(facts, field, doc_type):
    return next((f for f in facts if f["field"] == field and f["doc_type"] == doc_type), None)


def _norm(v):
    return re.sub(r"[^a-z0-9 ]", "", str(v).lower()).strip()


def _severity(diff, base):
    r = abs(diff) / base if base else 1
    return "High" if r >= 0.10 else "Medium" if r >= 0.03 else "Low"


def find_discrepancies(facts, tol=1.0):
    """Compare the same field across different document types. Never picks a winner."""
    by = {}
    for f in facts:
        by.setdefault(f["field"], []).append(f)
    out = []
    for field, items in by.items():
        for a, b in itertools.combinations(items, 2):
            if a["doc_type"] == b["doc_type"]:
                continue
            if isinstance(a["value"], (int, float)) and isinstance(b["value"], (int, float)):
                diff = b["value"] - a["value"]
                if abs(diff) > tol:
                    out.append({"field": field, "a": a, "b": b, "difference": diff,
                                "severity": _severity(diff, a["value"]), "action": "Underwriter review"})
            elif _norm(a["value"]) != _norm(b["value"]):
                ratio = difflib.SequenceMatcher(None, _norm(a["value"]), _norm(b["value"])).ratio()
                out.append({"field": field, "a": a, "b": b, "difference": None,
                            "severity": "Low" if ratio >= 0.65 else "Medium", "action": "Confirm name variant"})
    return out


def large_deposits(txns, threshold):
    """Non-payroll credits at or above the threshold with no source. A matching outflow of the
    same amount in a different statement (own-account transfer) counts as a source."""
    outs = {(t["document"], round(abs(t["amount"]), 2)) for t in txns if t["amount"] < 0}

    def sourced(t):
        return t.get("source_doc") or any(doc != t["document"] and a == round(t["amount"], 2) for doc, a in outs)

    return [t for t in txns if t["amount"] >= threshold
            and not re.search("payroll", t["desc"], re.I) and not sourced(t)]
