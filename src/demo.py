"""FICTIONAL DEMONSTRATION DATA. No real borrower information."""
TX = [(1, "09/02", "PAYROLL ABC CORP", 4100.00), (1, "09/05", "RENT PAYMENT", -1500.00),
      (1, "09/16", "PAYROLL ABC CORP", 4100.00), (2, "09/20", "TRANSFER FROM SAVINGS", 5000.00),
      (3, "09/24", "MOBILE DEPOSIT", 3200.00), (4, "09/28", "INCOMING WIRE DEPOSIT REF 88213", 15000.00)]
BANK = "BankStatement_Sep.pdf"
PROFILE_FIELDS = [  # section, label, fact field used when no manual value exists
    ("Borrower", "Name", "borrower_name"), ("Borrower", "Date of birth", None), ("Borrower", "Address", None),
    ("Borrower", "Co-borrower", None), ("Employment", "Employer", "employer"), ("Employment", "Position", None),
    ("Employment", "Start date", None), ("Employment", "Employment status", None),
    ("Employment", "Base income (monthly)", "monthly_income"), ("Employment", "Overtime / bonus / other", None),
    ("Assets", "Checking and savings", "assets_total"), ("Assets", "Retirement / investments", None),
    ("Liabilities", "Mortgage / auto / student loans", None), ("Liabilities", "Credit cards / other", None)]


def _doc(name, t, pages):
    return {"filename": name, "document_type": t, "upload_time": "2026-10-01 09:00",
            "page_count": pages, "processing_status": "Processed"}


def _f(field, value, doc, t, page, conf=0.95):
    return {"field": field, "value": value, "document": doc, "doc_type": t, "page": page, "confidence": conf}


def _bank_pages():
    pages = []
    for p in range(1, 5):
        lines = [f"{d} {s} {'-' if a < 0 else ''}${abs(a):,.2f}" for pg, d, s, a in TX if pg == p]
        t = f"Bank statement, statement period 09/01-09/30 (FICTIONAL), page {p}\n" + "\n".join(lines)
        pages.append(t + ("\nEnding balance: $147,500.00" if p == 1 else ""))
    return pages


def demo_loan():
    d, pay, app, apr = "Application.pdf", "PayStub_Sep.pdf", "Application.pdf", "Appraisal.pdf"
    return {
        "id": "DEMO-0001", "borrower": "James Carter", "programme": "Conventional 30-Year Fixed",
        "terms": {"loan_amount": 320000, "purchase_price": 400000, "property_value": 410000,
                  "monthly_income": 8200, "monthly_debt": 2100, "occupancy": "Primary residence",
                  "property_type": "Single-family detached",
                  "sources": {"loan_amount": "Application.pdf, Page 1", "purchase_price": "PurchaseContract.pdf, Page 1",
                              "property_value": "Appraisal.pdf, Page 1", "monthly_income": "PayStub_Sep.pdf, Page 1 (underwriter qualifying income)",
                              "monthly_debt": "CreditReport.pdf, Page 2"}},
        "docs": [_doc(app, "Loan application", 4), _doc(pay, "Pay stub", 1), _doc("W2_2025.pdf", "W-2", 1),
                 _doc(BANK, "Bank statement", 4), _doc("CreditReport.pdf", "Credit report", 3),
                 _doc(apr, "Appraisal", 12), _doc("PurchaseContract.pdf", "Purchase contract", 6)],
        "facts": [_f("monthly_income", 7900.0, app, "Loan application", 2), _f("monthly_income", 8500.0, pay, "Pay stub", 1),
                  _f("employer", "ABC Corp", app, "Loan application", 2), _f("employer", "ABC Corporation", pay, "Pay stub", 1),
                  _f("assets_total", 162000.0, app, "Loan application", 3), _f("assets_total", 147500.0, BANK, "Bank statement", 1),
                  _f("property_value", 425000.0, app, "Loan application", 1), _f("property_value", 410000.0, apr, "Appraisal", 1)],
        "txns": [{"document": BANK, "page": p, "date": dt, "desc": s, "amount": a, "source_doc": None} for p, dt, s, a in TX],
        "pages": {BANK: _bank_pages(), pay: ["Pay stub FICTIONAL\nEmployer: ABC Corporation\nGross monthly income: $8,500"],
                  app: ["Loan application FICTIONAL\nBorrower: James Carter\nEmployer: ABC Corp\nGross monthly income: $7,900\nTotal assets: $162,000\nProperty value: $425,000"]},
        "profile": {"Name": ("James Carter", "Application.pdf, Page 1"), "Date of birth": ("1987-04-12", "Application.pdf, Page 1"),
                    "Address": ("42 Maple Lane, Columbus, OH (fictional)", "Application.pdf, Page 1"), "Co-borrower": ("None", "Application.pdf, Page 1"),
                    "Position": ("Operations Analyst", "PayStub_Sep.pdf, Page 1"), "Start date": ("2019-03-01", "Application.pdf, Page 2"),
                    "Employment status": ("Full-time, salaried", "PayStub_Sep.pdf, Page 1"),
                    "Overtime / bonus / other": ("None documented", "PayStub_Sep.pdf, Page 1"),
                    "Retirement / investments": ("Not documented in file", "-"),
                    "Mortgage / auto / student loans": ("Auto $450, student $380 per month", "CreditReport.pdf, Page 2"),
                    "Credit cards / other": ("Minimum payments $1,270 per month", "CreditReport.pdf, Page 2")},
    }


def voe_resubmission():
    """Simulated resubmission: employment verification arrives with its own income figure."""
    f = "VOE_ABC.pdf"
    return (_doc(f, "Employment verification", 1),
            [_f("employer", "ABC Corporation", f, "Employment verification", 1),
             _f("monthly_income", 8200.0, f, "Employment verification", 1)])


def empty_loan():
    return {"id": "UPL-0001", "borrower": "Not identified", "programme": "Conventional 30-Year Fixed",
            "terms": {"loan_amount": 0, "purchase_price": 0, "property_value": 0, "monthly_income": 0,
                      "monthly_debt": 0, "occupancy": "", "property_type": "", "sources": {}},
            "docs": [], "facts": [], "txns": [], "pages": {}, "profile": {}}
