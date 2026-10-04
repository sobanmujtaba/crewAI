from src import demo, discrepancy_engine as de, document_processor as dp
from src.models import AnalysisResult


def test_income_discrepancy():
    d = [x for x in de.find_discrepancies(demo.demo_loan()["facts"]) if x["field"] == "monthly_income"]
    assert len(d) == 1 and {d[0]["a"]["value"], d[0]["b"]["value"]} == {7900.0, 8500.0}
    assert abs(d[0]["difference"]) == 600


def test_large_deposit():
    dep = de.large_deposits(demo.demo_loan()["txns"], 10000)
    assert [t["amount"] for t in dep] == [15000.0] and dep[0]["page"] == 4


def test_missing_document():
    rows = de.checklist(demo.demo_loan()["docs"], "Conventional 30-Year Fixed")
    assert [r["Document"] for r in rows if r["Status"] == "Missing"] == ["Employment verification"]


def test_regex_extraction_keeps_page():
    f = dp.extract_facts("a.pdf", "Pay stub", ["x", "Gross monthly income: $8,500"])
    assert f[0]["value"] == 8500.0 and f[0]["page"] == 2


def test_ai_schema():
    r = AnalysisResult(summary="s", recommendation="r", confidence=0.5)
    assert r.issues == [] and 0 <= r.confidence <= 1
