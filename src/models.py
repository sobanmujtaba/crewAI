"""Pydantic schemas used for validation."""
from pydantic import BaseModel, Field


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
