import pandas as pd
import numpy as np
import faiss
import pickle
import json
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
import time

PROCESSED  = Path("C:/full time/clinicalmind/data/processed")
FAISS_DIR  = Path("C:/full time/clinicalmind/data/faiss_db")
FAISS_DIR.mkdir(parents=True, exist_ok=True)

INDEX_PATH      = FAISS_DIR / "trials.index"
METADATA_PATH   = FAISS_DIR / "trials_metadata.pkl"
VECTORIZER_PATH = FAISS_DIR / "tfidf_vectorizer.pkl"


def embed_trials():
    print("Loading clean trials...")
    df = pd.read_csv(PROCESSED / "trials_clean.csv", low_memory=False)
    df = df.dropna(subset=["rag_text", "nct_id"]).reset_index(drop=True)
    print(f"  {len(df)} trials loaded")

    texts = df["rag_text"].tolist()

    # TF-IDF vectorization — no GPU, no DLL, pure sklearn
    print("Fitting TF-IDF vectorizer...")
    vectorizer = TfidfVectorizer(
        max_features=768,        # match typical embedding dim
        ngram_range=(1, 2),      # unigrams + bigrams
        sublinear_tf=True,       # log normalization
        min_df=2,
        max_df=0.95,
        strip_accents="unicode",
    )
    tfidf_matrix = vectorizer.fit_transform(texts)
    print(f"  TF-IDF matrix shape: {tfidf_matrix.shape}")

    # Convert to dense float32 for FAISS
    print("Converting to dense vectors...")
    vectors = tfidf_matrix.toarray().astype("float32")

    # L2 normalize so inner product = cosine similarity
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1
    vectors = vectors / norms

    # Build FAISS index
    print("Building FAISS index...")
    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)
    print(f"  Vectors in index: {index.ntotal}")

    # Build metadata store
    metadata_store = []
    for _, row in df.iterrows():
        metadata_store.append({
            "nct_id":        str(row.get("nct_id", "")),
            "title":         str(row.get("title", "")),
            "status_clean":  str(row.get("status_clean", "")),
            "phase_clean":   str(row.get("phase_clean", "")),
            "conditions":    str(row.get("conditions", "")),
            "interventions": str(row.get("interventions", "")),
            "sponsor":       str(row.get("sponsor", "")),
            "sponsor_class": str(row.get("sponsor_class", "")),
            "countries":     str(row.get("countries", "")),
            "enrollment":    str(row.get("enrollment", "")),
            "is_high_value": str(row.get("is_high_value", "")),
            "rag_text":      str(row.get("rag_text", ""))[:500],
        })

    # Save everything
    faiss.write_index(index, str(INDEX_PATH))
    with open(METADATA_PATH, "wb") as f:
        pickle.dump(metadata_store, f)
    with open(VECTORIZER_PATH, "wb") as f:
        pickle.dump(vectorizer, f)

    print(f"\nFAISS index saved to {INDEX_PATH}")
    print(f"Vectorizer saved to {VECTORIZER_PATH}")
    return index, metadata_store, vectorizer


def test_search(index, metadata_store, vectorizer, query: str, top_k: int = 3):
    print(f'\nQuery: "{query}"')

    q_vec = vectorizer.transform([query]).toarray().astype("float32")
    norm = np.linalg.norm(q_vec)
    if norm > 0:
        q_vec = q_vec / norm

    scores, indices = index.search(q_vec, top_k)

    for rank, (idx, score) in enumerate(zip(indices[0], scores[0])):
        if idx == -1:
            continue
        meta = metadata_store[idx]
        print(f"\n  Result {rank+1}  (score: {score:.3f})")
        print(f"  NCT ID : {meta['nct_id']}")
        print(f"  Title  : {meta['title'][:80]}")
        print(f"  Phase  : {meta['phase_clean']}  |  Status: {meta['status_clean']}")


if __name__ == "__main__":
    index, metadata_store, vectorizer = embed_trials()
    test_search(index, metadata_store, vectorizer, "phase 3 lung cancer immunotherapy")
    test_search(index, metadata_store, vectorizer, "diabetes GLP-1 weight loss recruiting")
    test_search(index, metadata_store, vectorizer, "alzheimer prevention older adults")