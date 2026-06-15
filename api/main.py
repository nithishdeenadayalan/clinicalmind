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