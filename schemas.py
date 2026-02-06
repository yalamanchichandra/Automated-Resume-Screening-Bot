from pydantic import BaseModel
from typing import List, Optional


class ResumeScore(BaseModel):
    name: str
    score: int
    similarity: Optional[float] = None
    reason: str


class AnalysisResponse(BaseModel):
    jd_summary: str
    results: List[ResumeScore]