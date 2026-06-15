import pandas as pd
import numpy as np
from pathlib import Path

RAW = Path("C:/full time/clinicalmind/data/raw/trials_flat.csv")
PROCESSED = Path("C:/full time/clinicalmind/data/processed")
PROCESSED.mkdir(parents=True, exist_ok=True)

def clean_trials(df: pd.DataFrame) -> pd.DataFrame:
    print(f"📥 Raw shape: {df.shape}")

    # ── 1. Drop duplicates ─────────────────────────────────────
    df = df.drop_duplicates(subset="nct_id", keep="first")
    print(f"After dedup: {df.shape}")

    # ── 2. Standardise status ──────────────────────────────────
    status_map = {
        "COMPLETED": "Completed",
        "RECRUITING": "Recruiting",
        "ACTIVE_NOT_RECRUITING": "Active",
        "TERMINATED": "Terminated",
        "WITHDRAWN": "Withdrawn",
        "SUSPENDED": "Suspended",
        "UNKNOWN": "Unknown",
        "NOT_YET_RECRUITING": "Not Yet Recruiting",
        "ENROLLING_BY_INVITATION": "Enrolling by Invitation",
    }
    df["status_clean"] = df["status"].map(status_map).fillna("Other")

    # ── 3. Parse dates ─────────────────────────────────────────
    for col in ["start_date", "completion_date"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    df["duration_days"] = (
        df["completion_date"] - df["start_date"]
    ).dt.days

    df["start_year"] = df["start_date"].dt.year

    # ── 4. Clean enrollment ────────────────────────────────────
    df["enrollment"] = pd.to_numeric(df["enrollment"], errors="coerce")
    # Cap extreme outliers (> 1M is likely a data error)
    df.loc[df["enrollment"] > 1_000_000, "enrollment"] = np.nan

    # ── 5. Phase normalisation ─────────────────────────────────
    phase_map = {
        "PHASE1": "Phase 1",
        "PHASE2": "Phase 2",
        "PHASE3": "Phase 3",
        "PHASE4": "Phase 4",
        "EARLY_PHASE1": "Early Phase 1",
        "NA": "N/A",
    }
    def normalise_phase(val):
        if not isinstance(val, str) or val == "":
            return "Not Specified"
        for k, v in phase_map.items():
            if k in val.upper():
                return v
        return val

    df["phase_clean"] = df["phase"].apply(normalise_phase)

    # ── 6. Create RAG text field ───────────────────────────────
    # This is the text that gets embedded into ChromaDB
    def build_rag_text(row):
        parts = []
        if row.get("title"):
            parts.append(f"Title: {row['title']}")
        if row.get("conditions"):
            parts.append(f"Conditions: {row['conditions']}")
        if row.get("interventions"):
            parts.append(f"Interventions: {row['interventions']}")
        if row.get("phase_clean"):
            parts.append(f"Phase: {row['phase_clean']}")
        if row.get("status_clean"):
            parts.append(f"Status: {row['status_clean']}")
        if row.get("brief_summary"):
            # Truncate to 500 chars to keep embeddings focused
            parts.append(f"Summary: {str(row['brief_summary'])[:500]}")
        if row.get("eligibility"):
            parts.append(f"Eligibility: {str(row['eligibility'])[:300]}")
        if row.get("primary_outcomes"):
            parts.append(f"Primary Outcomes: {row['primary_outcomes']}")
        return "\n".join(parts)

    print("🔨 Building RAG text field...")
    df["rag_text"] = df.apply(build_rag_text, axis=1)

    # ── 7. Drop rows with no useful text ──────────────────────
    df = df[df["rag_text"].str.len() > 50].reset_index(drop=True)

    # ── 8. Flag high-value trials ─────────────────────────────
    df["is_high_value"] = (
        (df["phase_clean"].isin(["Phase 3", "Phase 4"])) &
        (df["status_clean"].isin(["Completed", "Active", "Recruiting"])) &
        (df["enrollment"] >= 100)
    )

    print(f"\n✅ Clean shape: {df.shape}")
    print(f"🌟 High-value trials: {df['is_high_value'].sum()}")
    print(f"\nPhase breakdown:\n{df['phase_clean'].value_counts().head(8)}")
    print(f"\nStatus breakdown:\n{df['status_clean'].value_counts()}")
    print(f"\nMedian enrollment: {df['enrollment'].median():.0f}")
    print(f"Median duration (days): {df['duration_days'].median():.0f}")

    return df


def run():
    df_raw = pd.read_csv(RAW, low_memory=False)
    df_clean = clean_trials(df_raw)

    # Save full clean version
    out_full = PROCESSED / "trials_clean.csv"
    df_clean.to_csv(out_full, index=False)
    print(f"\n💾 Full clean CSV → {out_full}")

    # Save a lightweight version for fast loading (drop long text)
    df_lite = df_clean.drop(columns=["brief_summary", "eligibility", "rag_text"])
    out_lite = PROCESSED / "trials_lite.csv"
    df_lite.to_csv(out_lite, index=False)
    print(f"💾 Lite CSV       → {out_lite}")

    # Save high-value subset separately
    df_hv = df_clean[df_clean["is_high_value"]].copy()
    out_hv = PROCESSED / "trials_high_value.csv"
    df_hv.to_csv(out_hv, index=False)
    print(f"💾 High-value CSV → {out_hv}  ({len(df_hv)} trials)")

    return df_clean


if __name__ == "__main__":
    df = run()