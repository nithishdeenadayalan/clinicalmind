from fastapi import APIRouter, HTTPException
from api.services.search_service import search_service

router = APIRouter(prefix="/search", tags=["search"])

@router.post("/")
def search_trials(body: dict):
    query = body.get("query", "")
    top_k = body.get("top_k", 10)
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    try:
        results = search_service.search(query, top_k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"query": query, "total_results": len(results), "results": results}

@router.get("/{nct_id}")
def get_trial(nct_id: str):
    trial = search_service.get_by_nct_id(nct_id.upper())
    if not trial:
        raise HTTPException(status_code=404, detail=f"Trial {nct_id} not found")
    return trial