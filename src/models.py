"""Pydantic schemas used for validation."""
from pydantic import BaseModel, Field, field_validator

MAIN_KEYS = ("issue", "condition", "description", "text", "finding", "item", "summary")


def _text(x):
    """Turn a dict or any value into plain text."""
    if not isinstance(x, dict):
        return str(x)
    main = next((str(x[k]) for k in MAIN_KEYS if k in x), None)
    if main is None:
        return "; ".join(f"{k}: {v}" for k, v in x.items())
    extra = ", ".join(f"{k}: {v}" for k, v in x.items() if str(v) != main)
    return f"{main} ({extra})" if extra else main


class Fact(BaseModel):
    """One extracted value together with its source document and page."""
    field: str
    value: float | str
    document: str
    doc_type: str
    page: int
    confidence: float = 0.9


class AnalysisResult(BaseModel):
    """Structured output required from the LLM."""
    summary: str
    strengths: list[str] = []
    issues: list[str] = []
    missing_information: list[str] = []
    suggested_conditions: list[str] = []
    recommendation: str
    confidence: float = Field(ge=0, le=1)

    @field_validator("strengths", "issues", "missing_information", "suggested_conditions", mode="before")
    @classmethod
    def _items_to_text(cls, v):
        """Models sometimes return objects instead of strings. Flatten them to one line each."""
        if not isinstance(v, list):
            return [_text(v)] if v else []
        return [_text(i) for i in v]

    @field_validator("summary", "recommendation", mode="before")
    @classmethod
    def _to_text(cls, v):
        return _text(v)

    @field_validator("confidence", mode="before")
    @classmethod
    def _percent(cls, v):
        """Accept 85 or "85%" as 0.85."""
        v = float(str(v).strip("% "))
        return v / 100 if 1 < v <= 100 else v