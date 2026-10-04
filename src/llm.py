"""LLM access behind a small interface. Swap the provider here only."""
import json
import os

from src.models import AnalysisResult

NO_KEY = "AI analysis unavailable - configure an LLM API key to enable AI underwriting analysis."

SYSTEM = """Every list item must be a plain string, never an object.
You assist a human mortgage underwriter. Rules:
1. Never invent borrower information or guideline requirements.
2. Do not do arithmetic; use the supplied calculated metrics.
3. Use only the supplied guideline excerpts for guideline statements and cite their source and page.
4. Cite document and page for every fact. Never hide missing evidence or silently resolve a discrepancy.
5. Separate facts from interpretation. If evidence is inadequate say "Insufficient Information".
6. Do not make the final lending decision; the recommendation is advisory.
Return ONLY JSON with keys: summary, strengths, issues, missing_information, suggested_conditions,
recommendation, confidence (0 to 1)."""


class LLMUnavailable(Exception):
    pass


def available():
    return bool(os.getenv("GROQ_API_KEY"))


def _chat(system, user, json_mode=False):
    if not available():
        raise LLMUnavailable(NO_KEY)
    from groq import Groq
    kw = {"response_format": {"type": "json_object"}} if json_mode else {}
    r = Groq(api_key=os.getenv("GROQ_API_KEY")).chat.completions.create(
        model=os.getenv("GROQ_MODEL") or "llama-3.3-70b-versatile", temperature=0,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}], **kw)
    return r.choices[0].message.content


def analyse_loan(context):
    """Return a validated AnalysisResult."""
    return AnalysisResult(**json.loads(_chat(SYSTEM, json.dumps(context, default=str), True)))


def interpret_guideline(query, chunks):
    """Short plain-English reading of retrieved text only."""
    ctx = "\n".join(f"[{c['section']} p{c['page']}] {c['text']}" for c in chunks)
    return _chat("Explain only what the excerpts say. Do not add rules. Be brief.", f"Question: {query}\n{ctx}")
