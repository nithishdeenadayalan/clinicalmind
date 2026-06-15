import pandas as pd
import numpy as np
import faiss
import pickle
import json
from sentence_transformers import SentenceTransformer
from pathlib import Path
import time

PROCESSED  = Path("C:/full time/clinicalmind/data/processed")
FAISS_DIR  = Path("C:/full time/clinicalmind/data/faiss_db")
FAISS_DIR.mkdir(parents=True, exist_ok=True)

INDEX_PATH    = FAISS_DIR / "trials_neural.index"
METADATA_PATH = FAISS_DIR / "trials_neural_metadata.pkl"
IDS_PATH      = FAISS_DIR / "trials_neural_ids.json"

BATCH_SIZE = 512
MODEL_NAME = "all-MiniLM-L6-v2"


def embed_trials():
    print("Loading clean trials...")
    df = pd.read_csv(PROCESSED / "trials_clean.csv", low_memory=False)
    df = df.dropna(subset=["rag_text", "nct_id"]).reset_index(drop=True)
    print(f"  {len(df)} trials to embed")

    print("Loading neural embedding model...")
    model = SentenceTransformer(MODEL_NAME)
    dim = model.get_sentence_embedding_dimension()
    print(f"  Model loaded. Embedding dimension: {dim}")

    # Resume support
    if INDEX_PATH.exists() and METADATA_PATH.exists() and IDS_PATH.exists():
        print("  Existing index found — resuming...")
        index = faiss.read_index(str(INDEX_PATH))
        with open(METADATA_PATH, "rb") as f:
            metadata_store = pickle.load(f)
        with open(IDS_PATH, "r") as f:
            embedded_ids = set(json.load(f))
        print(f"  Already embedded: {len(embedded_ids)}")
    else:
        index = faiss.IndexFlatIP(dim)
        metadata_store = []
        embedded_ids = set()

    df_new = df[~df["nct_id"].isin(embedded_ids)].reset_index(drop=True)
    print(f"  New to embed: {len(df_new)}")

    if df_new.empty:
        print("All trials already embedded.")
        return index, metadata_store

    total = len(df_new)
    start_time = time.time()

    for start in range(0, total, BATCH_SIZE):
        batch = df_new.iloc[start : start + BATCH_SIZE]
        documents = batch["rag_text"].tolist()

        embeddings = model.encode(
            documents,
            batch_size=64,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True
        ).astype("float32")

        faiss.normalize_L2(embeddings)
        index.add(embeddings)

        for _, row in batch.iterrows():
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
            embedded_ids.add(str(row["nct_id"]))

        done = min(start + BATCH_SIZE, total)
        elapsed = time.time() - start_time
        rate = done / elapsed if elapsed > 0 else 1
        eta = (total - done) / rate / 60
        print(f"  {done:,}/{total:,}  ({done/total*100:.1f}%)  "
              f"{rate:.0f} trials/sec  ETA {eta:.1f} min")

        # Checkpoint every 20k
        if done % 20000 < BATCH_SIZE or done == total:
            faiss.write_index(index, str(INDEX_PATH))
            with open(METADATA_PATH, "wb") as f:
                pickle.dump(metadata_store, f)
            with open(IDS_PATH, "w") as f:
                json.dump(list(embedded_ids), f)
            print(f"  Checkpoint saved.")

    print(f"\nNeural index complete. Total vectors: {index.ntotal}")
    return index, metadata_store


def test_search(index, metadata_store, query: str, top_k: int = 3):
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL_NAME)
    print(f'\nQuery: "{query}"')
    q_vec = model.encode([query], normalize_embeddings=True,
                         convert_to_numpy=True).astype("float32")
    faiss.normalize_L2(q_vec)
    scores, indices = index.search(q_vec, top_k)
    for rank, (idx, score) in enumerate(zip(indices[0], scores[0])):
        if idx == -1:
            continue
        meta = metadata_store[idx]
        print(f"  Result {rank+1}  (score: {score:.3f})")
        print(f"  NCT ID : {meta['nct_id']}")
        print(f"  Title  : {meta['title'][:80]}")
        print(f"  Phase  : {meta['phase_clean']}  |  Status: {meta['status_clean']}")


if __name__ == "__main__":
    index, metadata_store = embed_trials()
    test_search(index, metadata_store, "GLP-1 semaglutide diabetes weight loss")
    test_search(index, metadata_store, "pembrolizumab lung cancer phase 3")
    test_search(index, metadata_store, "alzheimer prevention amyloid")