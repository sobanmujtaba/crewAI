"""AI Mortgage Underwriting Assistant (Streamlit). The human underwriter decides."""
import os

import pandas as pd
import streamlit as st

from src import calculations as calc, database as db, demo, discrepancy_engine as de
from src import document_processor as dp, guideline_rag as gr, llm, underwriting as uw

st.set_page_config(page_title="AI Mortgage Underwriting Assistant", page_icon=":material/account_balance:", layout="wide")
st.markdown("<style>[data-testid=stMetricValue]{font-size:1.35rem}.block-container{padding-top:1.5rem}</style>",
            unsafe_allow_html=True)

# Load API settings from .env or Streamlit secrets (never hard-coded)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass
for k in ("GROQ_API_KEY", "GROQ_MODEL"):
    try:
        if k in st.secrets:
            os.environ.setdefault(k, str(st.secrets[k]))
    except Exception:
        pass  # no secrets file is fine

money = lambda v: f"${v:,.0f}"
pc = lambda v: f"{v:.2f}%" if v is not None else "n/a"
PAGES = ["Dashboard", "Borrower", "Documents", "Financial Analysis", "Discrepancies", "Guidelines",
         "AI Underwriting", "Conditions", "Audit Trail"]
STATUSES = ["Open", "Submitted", "Satisfied", "Rejected", "Waived"]
S = st.session_state
if "loans" not in S:
    S.loans = {"Demo loan": demo.demo_loan(), "Uploaded loan": demo.empty_loan()}
    S.current_loan, S.analysis, S.baseline, S.hits, S.interp = "Demo loan", {}, {}, [], ""


def metrics_row(items):
    for col, (k, v) in zip(st.columns(len(items)), items):
        col.metric(k, v)


# ---------------- Sidebar ----------------
with st.sidebar:
    st.markdown("### AI Mortgage Underwriter")
    st.radio("Loan file", list(S.loans), key="current_loan")
    page = st.radio("Loan", PAGES, key="page")
    loan = S.loans[S.current_loan]
    last = db.decisions(loan["id"])
    st.divider()
    st.caption(f"**Current Loan**  \nLoan ID: {loan['id']}  \nBorrower: {loan['borrower']}  \n"
               f"Programme: {loan['programme']}  \nStatus: {last[0]['decision'] if last else 'Under review'}")
    with st.expander("Settings"):
        cfg = dict(deposit_threshold=st.number_input("Large deposit threshold ($)", value=10000, step=1000),
                   closing_pct=st.number_input("Closing costs % of price (assumption)", value=3.0),
                   rate=st.number_input("Interest rate % (assumption)", value=6.5))

# ---------------- Shared computations ----------------
t = loan["terms"]
bank = de.fact(loan["facts"], "assets_total", "Bank statement")
m = calc.summary(t, bank["value"] if bank else 0, cfg)
cks = de.checklist(loan["docs"], loan["programme"])
findings = uw.build_findings(loan, cfg, gr.search)
S.findings, S.documents = findings, loan["docs"]
lid = loan["id"]
conds = db.conditions(lid)


def show_finding(f):
    """Expandable evidence for one finding: document, page, value, text, guideline."""
    with st.expander(f"[{f['severity']}] {f['title']}"):
        e = f["evidence"]
        st.markdown(f"**Finding:** {f['detail']}  \n**Document:** {e['document']}  \n**Page:** {e['page'] or '-'}  \n"
                    f"**Extracted value:** {e['value'] or '-'}  \n**Suggested action:** {f['action']}")
        if e["text"]:
            st.code(e["text"], language=None)
        g = f.get("guideline")
        if g:
            st.markdown(f"**Guideline:** {g['source']}, {g['section']}, page {g['page']} (effective {g['effective_date']})")
            st.caption("Source text: " + g["text"])


def decision_panel():
    st.subheader("UNDERWRITER DECISION")
    st.caption("This is the human underwriter's decision. The AI does not decide.")
    dec = st.radio("Decision", ["Approve", "Conditional Approval", "Suspend", "Decline", "Request Information"],
                   horizontal=True, index=None)
    user = st.text_input("Underwriter", "Underwriter")
    why = st.text_area("Reason (required)")
    if st.button("Record decision"):
        if dec and why.strip():
            db.add_decision(lid, dec, why.strip(), user)
            st.success("Decision recorded")
        else:
            st.error("Select a decision and enter a reason.")
    if db.decisions(lid):
        st.dataframe(pd.DataFrame(db.decisions(lid))[["ts", "decision", "reason", "user"]], hide_index=True, use_container_width=True)


# ---------------- Pages ----------------
if page == "Dashboard":
    if lid.startswith("DEMO"):
        st.info("FICTIONAL DEMONSTRATION DATA")
    st.error("UNDERWRITER REVIEW REQUIRED. AI output is advisory, not a decision.")
    st.caption("Workflow: Upload > Identify > Extract > Validate > Calculate > Check > Compare > Guidelines > AI analysis > Conditions > Human decision")
    metrics_row([("Borrower", loan["borrower"]), ("Loan ID", lid), ("Programme", loan["programme"]),
                 ("Loan amount", money(t["loan_amount"])), ("Purchase price", money(t["purchase_price"]))])
    metrics_row([("Property value", money(t["property_value"])), ("LTV", pc(m["ltv"])), ("DTI", pc(m["dti"])),
                 ("Occupancy", t["occupancy"] or "n/a"), ("Property type", t["property_type"] or "n/a")])
    st.divider()
    need = [r for r in cks if r["Status"] != "Not Applicable"]
    ai = S.analysis.get(lid)
    metrics_row([("Documents", f"{sum(r['Status'] == 'Complete' for r in need)} / {len(need)} Complete"),
                 ("Open Issues", len(findings)),
                 ("Conditions", f"{sum(c['status'] in ('Open', 'Submitted') for c in conds)} Open"),
                 ("Guideline Findings", sum(bool(f.get("guideline")) for f in findings)),
                 ("AI Confidence", f"{ai.confidence:.0%}" if ai else "n/a")])
    st.subheader("Open issues")
    for f in findings:
        show_finding(f)

elif page == "Borrower":
    st.subheader("Loan terms")
    with st.form("terms"):
        c = st.columns(3)
        for col, k in zip(c * 2, ["loan_amount", "purchase_price", "property_value", "monthly_income", "monthly_debt"]):
            t[k] = col.number_input(k.replace("_", " ").title(), value=float(t[k]), step=100.0)
        t["occupancy"] = c[2].text_input("Occupancy", t["occupancy"])
        t["property_type"] = c[0].text_input("Property type", t["property_type"])
        loan["programme"] = c[1].selectbox("Programme", list(de.REQUIRED), index=list(de.REQUIRED).index(loan["programme"]))
        if st.form_submit_button("Save"):
            db.log(lid, "Loan terms edited by underwriter")
            st.rerun()
    for sec in ["Borrower", "Employment", "Assets", "Liabilities"]:
        st.subheader(sec)
        rows = []
        for s, label, ff in demo.PROFILE_FIELDS:
            if s != sec:
                continue
            val, src = loan["profile"].get(label, (None, None))
            if val is None and ff:  # fall back to extracted facts
                fc = next((x for x in loan["facts"] if x["field"] == ff), None)
                val, src = (uw.fmt(ff, fc["value"]), f"{fc['document']}, Page {fc['page']}") if fc else (None, None)
            rows.append({"Field": label, "Value": val or "Not available", "Source": src or "-"})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

elif page == "Documents":
    files = st.file_uploader("Upload borrower documents", type=["pdf", "docx", "txt"], accept_multiple_files=True)
    st.caption(f"Files are added to the selected loan file: {S.current_loan}")
    if files and st.button("Process documents"):
        for f in files:
            if any(d["filename"] == f.name for d in loan["docs"]):
                continue
            doc, pages, facts, txns = dp.process_file(f.name, f.getvalue())
            loan["docs"].append(doc); loan["pages"][f.name] = pages
            loan["facts"] += facts; loan["txns"] += txns
            db.log(lid, "Document uploaded", f"{f.name} classified as {doc['document_type']}")
            db.log(lid, "Extraction", f"{f.name}: {len(facts)} fields, {len(txns)} transactions, {doc['processing_status']}")
            for x in de.large_deposits(txns, cfg["deposit_threshold"]):
                db.log(lid, "Potential large deposit detected", f"${x['amount']:,.0f} in {x['document']} p{x['page']}")
        uw.fill_terms(loan)
        st.rerun()
    for d in loan["docs"]:
        if "failed" in d["processing_status"]:
            st.error(f"{d['filename']}: Unable to reliably extract this document. Manual review required.")
    st.subheader("Documents")
    st.dataframe(pd.DataFrame(loan["docs"]), hide_index=True, use_container_width=True)
    st.subheader("Completeness checklist")
    st.dataframe(pd.DataFrame(cks), hide_index=True, use_container_width=True)
    if loan["pages"]:
        st.subheader("Document viewer")
        name = st.selectbox("Document", list(loan["pages"]))
        for i, txt in enumerate(loan["pages"][name], 1):
            with st.expander(f"{name}, Page {i}"):
                st.code(txt or "(no text)", language=None)
    st.subheader("Resubmission review")
    c1, c2 = st.columns(2)
    if c1.button("Save current state as baseline"):
        S.baseline[lid] = {"titles": {f["id"]: f["title"] for f in findings}, "facts": [dict(x) for x in loan["facts"]]}
        db.log(lid, "Baseline review saved")
    if lid.startswith("DEMO") and c2.button("Simulate resubmission (add employment verification)"):
        d, fa = demo.voe_resubmission()
        if not any(x["filename"] == d["filename"] for x in loan["docs"]):
            loan["docs"].append(d); loan["facts"] += fa
            db.log(lid, "Document uploaded", d["filename"])
            st.rerun()
    b = S.baseline.get(lid)
    if b:
        res, unres, new = uw.compare_snapshots(b["titles"], findings)
        st.markdown("**Resolved:** " + ("; ".join(res) or "none"))
        st.markdown("**Still unresolved:** " + ("; ".join(unres) or "none"))
        st.markdown("**New issue:** " + ("; ".join(new) or "none"))
        prev = {(x["field"], x["doc_type"]): x for x in b["facts"]}
        rows = [{"Field": x["field"], "Previous value": prev[k]["value"], "New value": x["value"],
                 "Source": f"{x['document']}, Page {x['page']}"}
                for x in loan["facts"] if (k := (x["field"], x["doc_type"])) in prev and prev[k]["value"] != x["value"]]
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

elif page == "Financial Analysis":
    src = t.get("sources", {})
    st.subheader("DTI")
    st.code(f"{money(t['monthly_debt'])} monthly debt\n/\n{money(t['monthly_income'])} qualifying income\n= {pc(m['dti'])}", language=None)
    st.subheader("LTV")
    st.code(f"{money(t['loan_amount'])} loan amount\n/\n{money(t['property_value'])} property value\n= {pc(m['ltv'])}", language=None)
    st.subheader("Funds to close and reserves")
    st.code(f"Down payment {money(t['purchase_price'] - t['loan_amount'])} + closing costs at {cfg['closing_pct']}% (assumption)\n"
            f"= {money(m['required'])} required\nVerified assets {money(m['assets'])} - required = {money(m['reserves'])} reserves\n"
            f"Payment at {cfg['rate']}% over 30 years (assumption): {money(m['payment'])} => {m['reserve_months'] or 'n/a'} months", language=None)
    st.subheader("Inputs and sources")
    st.dataframe(pd.DataFrame([{"Input": k, "Value": t[k], "Source": src.get(k, "Entered manually / not recorded")}
                               for k in ["loan_amount", "purchase_price", "property_value", "monthly_income", "monthly_debt"]]),
                 hide_index=True, use_container_width=True)

elif page == "Discrepancies":
    st.caption("The system never decides which source is correct.")
    items = [f for f in findings if f["kind"] in ("discrepancy", "deposit")]
    if not items:
        st.success("No discrepancies or large deposits detected.")
    for f in items:
        if f["kind"] == "discrepancy":
            p = f["pair"]
            st.markdown(f"**DISCREPANCY: {p['field'].replace('_', ' ').title()}**  \nDocument A: {p['a']['doc_type']}, {uw.fmt(p['field'], p['a']['value'])}  \n"
                        f"Document B: {p['b']['doc_type']}, {uw.fmt(p['field'], p['b']['value'])}  \n"
                        f"Difference: {uw.fmt(p['field'], abs(p['difference'])) if p['difference'] is not None else 'text differs'}  \n"
                        f"Severity: {p['severity']}  \nRecommended action: {p['action']}")
        else:
            e = f["evidence"]
            st.markdown(f"**POTENTIAL LARGE DEPOSIT**  \nAmount: {e['value']}  \nDocument: {e['document']}, Page {e['page']}  \n"
                        f"Status: Source not documented  \nSuggested action: {f['action']}")
        show_finding(f)
        st.divider()

elif page == "Guidelines":
    q = st.text_input("Search underwriting guidelines...", "How should an unexplained large deposit be documented?")
    if st.button("Search"):
        S.hits, S.interp = gr.search(q, 3), ""
        db.log(lid, "Guideline search", q)
        if S.hits:
            try:
                S.interp = llm.interpret_guideline(q, S.hits)
            except llm.LLMUnavailable as e:
                S.interp = str(e)
            except Exception as e:
                S.interp = f"AI interpretation failed: {e}"
    for h in S.hits:
        st.markdown(f"**Relevant Guideline**  \nSource: {h['source']} (v{h['version']})  \nSection: {h['section']}  \n"
                    f"Effective: {h['effective_date']}  \nDocument: {h['file']}, Page {h['page']}  \nMatch score: {h['score']}")
        st.caption("SOURCE TEXT")
        st.code(h["text"], language=None)
    if S.hits:
        st.caption("AI INTERPRETATION (not source text)")
        st.write(S.interp)

elif page == "AI Underwriting":
    if not llm.available():
        st.warning(llm.NO_KEY)
    st.markdown(f"**Rule-based status:** {len(findings)} open issues, {sum(r['Status'] == 'Missing' for r in cks)} missing documents.")
    if st.button("Run AI analysis", disabled=not llm.available()):
        try:
            with st.spinner("Analysing"):
                S.analysis[lid] = llm.analyse_loan(uw.build_context(loan, m, cks, findings))
            db.log(lid, "AI analysis run")
        except Exception as e:
            st.error(f"AI analysis failed: {e}")
    a = S.analysis.get(lid)
    if a:
        st.subheader("AI Underwriting Summary")
        st.write(a.summary)
        for title, items in [("Supporting Findings", a.strengths), ("Issues", a.issues), ("Missing Information", a.missing_information)]:
            st.markdown(f"**{title}**")
            for i in items:
                st.write("- " + i)
        st.markdown("**Suggested Conditions**")
        for i, c in enumerate(a.suggested_conditions):
            c1, c2 = st.columns([6, 1])
            c1.write(f"{i + 1}. {c}")
            if c2.button("Accept", key=f"ai{i}") and c not in [x["condition"] for x in conds]:
                db.add_condition(lid, c, "AI analysis", "", "", "AI (accepted by underwriter)")
                st.rerun()
        st.info(f"AI recommendation (advisory): {a.recommendation}  \nHuman underwriter decision required.  \nConfidence: {a.confidence:.0%}")
    st.subheader("Evidence")
    for f in findings:
        show_finding(f)
    st.divider()
    decision_panel()

elif page == "Conditions":
    st.subheader("Suggested conditions (rule-based)")
    have = {c["condition"] for c in conds}
    for i, s in enumerate(uw.suggest_conditions(findings)):
        c1, c2 = st.columns([6, 1])
        c1.write(s["condition"])
        if s["condition"] in have:
            c2.caption("Added")
        elif c2.button("Accept", key=f"acc{i}"):
            db.add_condition(lid, s["condition"], s["reason"], s["evidence"], s["guideline"], "Rules (accepted by underwriter)")
            st.rerun()
    st.subheader("Conditions")
    for c in conds:
        with st.expander(f"#{c['id']} [{c['status']}] {c['condition'][:90]}"):
            txt = st.text_area("Condition", c["condition"], key=f"t{c['id']}")
            stat = st.selectbox("Status", STATUSES, index=STATUSES.index(c["status"]), key=f"s{c['id']}")
            st.caption(f"Reason: {c['reason']} | Evidence: {c['evidence']} | Guideline: {c['guideline'] or '-'} | "
                       f"Created by {c['created_by']} on {c['created_at']}")
            b = st.columns(4)
            if b[0].button("Save", key=f"sv{c['id']}"):
                db.update_condition(lid, c["id"], condition=txt, status=stat); st.rerun()
            if b[1].button("Mark satisfied", key=f"ok{c['id']}"):
                db.update_condition(lid, c["id"], status="Satisfied"); st.rerun()
            if b[2].button("Request info", key=f"ri{c['id']}"):
                db.update_condition(lid, c["id"], status="Submitted"); st.rerun()
            if b[3].button("Delete", key=f"dl{c['id']}"):
                db.delete_condition(lid, c["id"]); st.rerun()
    with st.form("manual"):
        new = st.text_input("Add manual condition")
        if st.form_submit_button("Add") and new.strip():
            db.add_condition(lid, new.strip(), "Manual", "", "", "Underwriter")
            st.rerun()

elif page == "Audit Trail":
    rows = db.audit(lid)
    st.code("\n\n".join(f"{r['ts']}\n{r['event']}: {r['detail']}" for r in rows) or "No events yet.", language=None)
