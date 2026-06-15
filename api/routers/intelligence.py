from fastapi import APIRouter, HTTPException
from api.services.search_service import search_service
from api.services.claude_service import ask_claude

router = APIRouter(prefix="/intelligence", tags=["intelligence"])

@router.post("/")
def get_intelligence(body: dict):
    query = body.get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    try:
        trials = search_service.search(query, top_k=8)
        answer = ask_claude(query, trials)
        sources = [t["nct_id"] for t in trials if t.get("nct_id")]
        return {"query": query, "answer": answer, "sources": sources}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))