import faiss
import pickle
import numpy as np
from pathlib import Path

FAISS_DIR = Path("C:/full time/clinicalmind/data/faiss_db")
MODEL_NAME = "all-MiniLM-L6-v2"

class SearchService:
    def __init__(self):
        self.index = None
        self.metadata = None
        self.model = None
        self.vectorizer = None
        self.mode = None

    def load(self):
        neural_index = FAISS_DIR / "trials_neural.index"
        neural_meta  = FAISS_DIR / "trials_neural_metadata.pkl"

        if neural_index.exists() and neural_meta.exists():
            print("Loading neural FAISS index...")
            self.index = faiss.read_index(str(neural_index))
            with open(neural_meta, "rb") as f:
                self.metadata = pickle.load(f)
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(MODEL_NAME)
            self.mode = "neural"
        else:
            print("Loading TF-IDF FAISS index...")
            from sklearn.feature_extraction.text import TfidfVectorizer
            self.index = faiss.read_index(str(FAISS_DIR / "trials.index"))
            with open(FAISS_DIR / "trials_metadata.pkl", "rb") as f:
                self.metadata = pickle.load(f)
            with open(FAISS_DIR / "tfidf_vectorizer.pkl", "rb") as f:
                self.vectorizer = pickle.load(f)
            self.mode = "tfidf"

        print(f"  Loaded {self.index.ntotal} vectors ({self.mode} mode)")

    def search(self, query: str, top_k: int = 10) -> list:
        if self.index is None:
            self.load()

        if self.mode == "neural":
            q_vec = self.model.encode(
                [query], normalize_embeddings=True, convert_to_numpy=True
            ).astype("float32")
            faiss.normalize_L2(q_vec)
        else:
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