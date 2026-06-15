from pathlib import Path

files = {}

files["api/services/search_service.py"] = """
import faiss
import pickle
import numpy as np
from pathlib import Path

FAISS_DIR = Path("C:/full time/clinicalmind/data/faiss_db")

class SearchService:
    def __init__(self):
        self.index = None
        self.metadata = None
        self.vectorizer = None

    def load(self):
        print("Loading FAISS index...")
        self.index = faiss.read_index(str(FAISS_DIR / "trials.index"))
        with open(FAISS_DIR / "trials_metadata.pkl", "rb") as f:
            self.metadata = pickle.load(f)
        with open(FAISS_DIR / "tfidf_vectorizer.pkl", "rb") as f:
            self.vectorizer = pickle.load(f)
        print(f"  Loaded {self.index.ntotal} vectors")

    def search(self, query: str, top_k: int = 10) -> list:
        if self.index is None:
            self.load()
        q_vec = self.vectorizer.transform([query]).toarray().astype("float32")
        norm = np.linalg.norm(q_vec)
        if norm > 0:
            q_vec = q_vec / norm
        scores, indices = self.index.search(q_vec, top_k)
        results = []
        for idx, score in zip(indices[0], scores[0]):
            if idx == -1:
                continue
            meta = self.metadata[idx]
            results.append({**meta, "score": float(score)})
        return results

    def get_by_nct_id(self, nct_id: str):
        if self.metadata is None:
            self.load()
        for meta in self.metadata:
            if meta["nct_id"] == nct_id:
                return meta
        return None

search_service = SearchService()
""".strip()

files["api/routers/search.py"] = """
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
""".strip()

files["api/routers/intelligence.py"] = """
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
""".strip()

files["api/services/claude_service.py"] = """
import anthropic
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path("C:/full time/clinicalmind/.env"))
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = \"\"\"You are ClinicalMind, an expert AI assistant for clinical trial intelligence.
You help pharmaceutical researchers, CROs, and medical professionals analyze clinical trial data.
When answering questions:
- Be precise and cite specific NCT IDs when referencing trials
- Highlight phase, status, enrollment size, and sponsor when relevant
- Flag high-value trials (Phase 3/4, large enrollment, completed) prominently
- Use professional medical and pharmaceutical terminology
\"\"\"

def ask_claude(query: str, trial_context: list) -> str:
    context_text = ""
    for i, trial in enumerate(trial_context[:8], 1):
        context_text += f\"\"\"
Trial {i}:
  NCT ID: {trial.get('nct_id')}
  Title: {trial.get('title')}
  Phase: {trial.get('phase_clean')}
  Status: {trial.get('status_clean')}
  Conditions: {trial.get('conditions')}
  Interventions: {trial.get('interventions')}
  Sponsor: {trial.get('sponsor')} ({trial.get('sponsor_class')})
  Enrollment: {trial.get('enrollment')}
  Summary: {trial.get('rag_text', '')[:300]}
\"\"\"
    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Question: {query}\\n\\nContext:\\n{context_text}"
        }]
    )
    return message.content[0].text
""".strip()

files["api/main.py"] = """
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import search, intelligence
from api.services.search_service import search_service

app = FastAPI(
    title="ClinicalMind API",
    description="AI-powered clinical trial intelligence platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    search_service.load()

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "vectors_loaded": search_service.index.ntotal if search_service.index else 0
    }

app.include_router(search.router)
app.include_router(intelligence.router)
""".strip()

for path, content in files.items():
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"Written: {path}")

print("\nAll files written. Run: python -m uvicorn api.main:app --reload --port 8000")