"""Combine checks into findings, conditions and AI context."""
from src import discrepancy_engine as de

MONEY = {"monthly_income", "assets_total", "property_value", "loan_amount", "purchase_price"}


def fmt(field, v):
    return f"${v:,.0f}" if field in MONEY and isinstance(v, (int, float)) else str(v)


def build_findings(loan, cfg, search=None):
    """Each finding carries evidence (document, page, value) and an optional guideline hit."""
    out = []
    for r in de.checklist(loan["docs"], loan["programme"]):
        if r["Status"] in ("Missing", "Outdated", "Review Required"):
            out.append(dict(id="doc:" + r["Document"], kind="document", title=f"{r['Document']}: {r['Status']}",
                            severity="High" if r["Status"] == "Missing" else "Medium", detail=r["Note"],
                            evidence=dict(document=r["Source"], page=None, value=None, text=""),
                            query=f"documentation requirements {r['Document']}", action="Request document from borrower"))
    for d in de.find_discrepancies(loan["facts"]):
        a, b, fld = d["a"], d["b"], d["field"]
        fa, fb = fmt(fld, a["value"]), fmt(fld, b["value"])
        diff = fmt(fld, abs(d["difference"])) if d["difference"] is not None else "text differs"
        out.append(dict(id=f"disc:{fld}:{a['doc_type']}:{b['doc_type']}", kind="discrepancy",
                        title=f"{fld.replace('_', ' ').title()} differs: {fa} vs {fb}", severity=d["severity"],
                        detail=f"{a['doc_type']} ({a['document']}, p{a['page']}): {fa}. {b['doc_type']} ({b['document']}, p{b['page']}): {fb}. Difference: {diff}.",
                        evidence=dict(document=f"{a['document']} / {b['document']}", page=f"{a['page']} / {b['page']}",
                                      value=f"{fa} vs {fb}", text=""),
                        query=f"{fld.replace('_', ' ')} differs between documents", action=d["action"], pair=d))
    for t in de.large_deposits(loan["txns"], cfg["deposit_threshold"]):
        line = f"{t['date']} {t['desc']} ${t['amount']:,.2f}"
        out.append(dict(id=f"dep:{t['document']}:{t['page']}:{t['amount']}", kind="deposit",
                        title=f"Potential large deposit: ${t['amount']:,.0f}", severity="High",
                        detail=f"{line}. Status: source not documented.",
                        evidence=dict(document=t["document"], page=t["page"], value=f"${t['amount']:,.0f}", text=line),
                        query="how should an unexplained large deposit be documented",
                        action="Obtain documentation establishing the source of funds."))
    if search:
        for f in out:
            hits = search(f["query"], 1)
            f["guideline"] = hits[0] if hits else None
    return out


def suggest_conditions(findings):
    """Rule-based condition drafts (work without an API key)."""
    out = []
    for f in findings:
        g = f.get("guideline")
        gl = f"{g['source']}, {g['section']}, p{g['page']}" if g else ""
        ev = f"{f['evidence']['document']} p{f['evidence']['page']}"
        if f["kind"] == "document":
            c = f"Provide {f['title'].split(':')[0].lower()}."
        elif f["kind"] == "deposit":
            c = f"Provide documentation supporting the source of the {f['evidence']['value']} deposit ({f['evidence']['text']})."
        else:
            c = f"Provide documentation reconciling: {f['title']}."
        out.append(dict(condition=c, reason=f["title"], evidence=ev, guideline=gl))
    return out


def fill_terms(loan):
    """Fill empty loan terms and borrower name from extracted facts (with sources)."""
    t = loan["terms"]
    for field, dt in [("loan_amount", None), ("purchase_price", None), ("property_value", "Appraisal"),
                      ("monthly_income", "Pay stub")]:
        for f in loan["facts"]:
            if f["field"] == field and (dt is None or f["doc_type"] == dt) and not t.get(field):
                t[field] = f["value"]
                t.setdefault("sources", {})[field] = f"{f['document']}, Page {f['page']}"
    for f in loan["facts"]:
        if f["field"] == "borrower_name" and loan["borrower"].startswith("Not"):
            loan["borrower"] = str(f["value"])


def compare_snapshots(prev_titles, findings):
    """prev_titles: {id: title} from the saved baseline. Returns resolved, unresolved, new."""
    cur = {f["id"]: f["title"] for f in findings}
    return ([t for i, t in prev_titles.items() if i not in cur],
            [t for i, t in cur.items() if i in prev_titles],
            [t for i, t in cur.items() if i not in prev_titles])


def build_context(loan, metrics, checklist, findings):
    return dict(borrower=loan["borrower"], programme=loan["programme"], loan_terms=loan["terms"],
                calculated_metrics=metrics, document_checklist=checklist,
                findings=[{k: v for k, v in f.items() if k not in ("pair", "guideline")} for f in findings],
                guideline_excerpts=[f["guideline"] for f in findings if f.get("guideline")])
