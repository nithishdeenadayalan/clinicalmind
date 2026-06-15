from pydantic import BaseModel
from typing import Optional, List

class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    filters: Optional[dict] = None

class TrialResult(BaseModel):
    nct_id: str
    title: str
    status: str
    phase: str
    conditions: str
    interventions: str
    sponsor: str
    countries: str
    enrollment: str
    score: float
    is_high_value: str

class SearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[TrialResult]

class IntelligenceRequest(BaseModel):
    query: str
    context_trials: Optional[List[str]] = None  # list of nct_ids

class IntelligenceResponse(BaseModel):
    query: str
    answer: str
    sources: List[str]