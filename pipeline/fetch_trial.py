import os
import requests
import pandas as pd
import json
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path("C:/full time/clinicalmind/.env"))

BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
RAW_DATA_DIR = Path("C:/full time/clinicalmind/data/raw")
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

def test_api_connection():
    """Quick sanity check — fetch just 5 trials."""
    params = {
        "query.cond": "cancer",
        "pageSize": 5,
        "format": "json",
    }
    print("🔍 Testing API connection...")
    resp = requests.get(BASE_URL, params=params, timeout=30)
    print(f"  Status code: {resp.status_code}")
    print(f"  URL called: {resp.url}")
    
    if resp.status_code != 200:
        print(f"  ERROR body: {resp.text[:500]}")
        return None
    
    data = resp.json()
    studies = data.get("studies", [])
    total = data.get("totalCount", "unknown")
    print(f"  Total available: {total}")
    print(f"  Studies in this page: {len(studies)}")
    
    if studies:
        # Print the raw keys so we can see the structure
        first = studies[0]
        print(f"\n  Top-level keys in study[0]: {list(first.keys())}")
        proto = first.get("protocolSection", {})
        print(f"  protocolSection keys: {list(proto.keys())}")
    
    return data

def fetch_trials_batch(condition: str, page_token: str = None, page_size: int = 1000):
    params = {
        "query.cond": condition,
        "pageSize": page_size,
        "format": "json",
        # REMOVED the 'fields' param — it was likely causing empty responses
    }
    if page_token:
        params["pageToken"] = page_token

    resp = requests.get(BASE_URL, params=params, timeout=60)
    resp.raise_for_status()
    return resp.json()

def safe_get(d: dict, *keys, default=""):
    """Safely traverse nested dicts."""
    for key in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(key, {})
    return d if d != {} else default

def parse_study(proto: dict) -> dict:
    """Parse one protocolSection into a flat row."""
    id_mod       = proto.get("identificationModule", {})
    status_mod   = proto.get("statusModule", {})
    design_mod   = proto.get("designModule", {})
    desc_mod     = proto.get("descriptionModule", {})
    elig_mod     = proto.get("eligibilityModule", {})
    sponsor_mod  = proto.get("sponsorCollaboratorsModule", {})
    cond_mod     = proto.get("conditionsModule", {})
    arms_mod     = proto.get("armsInterventionsModule", {})
    outcomes_mod = proto.get("outcomesModule", {})
    contacts_mod = proto.get("contactsLocationsModule", {})

    # Interventions
    interventions = arms_mod.get("interventions", [])
    intv_names = [i.get("name", "") for i in interventions]
    intv_types = [i.get("type", "") for i in interventions]

    # Primary outcomes
    primary_outcomes = outcomes_mod.get("primaryOutcomes", [])
    primary_measures = [o.get("measure", "") for o in primary_outcomes]

    # Locations / countries
    locations = contacts_mod.get("locations", [])
    countries = list({loc.get("country", "") for loc in locations if loc.get("country")})

    # Phase — comes as a list e.g. ["PHASE2", "PHASE3"]
    phases = design_mod.get("phases", [])
    phase_str = ", ".join(phases) if phases else ""

    return {
        "nct_id":            id_mod.get("nctId", ""),
        "title":             id_mod.get("briefTitle", ""),
        "official_title":    id_mod.get("officialTitle", ""),
        "status":            status_mod.get("overallStatus", ""),
        "phase":             phase_str,
        "study_type":        design_mod.get("studyType", ""),
        "enrollment":        safe_get(design_mod, "enrollmentInfo", "count"),
        "start_date":        safe_get(status_mod, "startDateStruct", "date"),
        "completion_date":   safe_get(status_mod, "completionDateStruct", "date"),
        "brief_summary":     desc_mod.get("briefSummary", "").strip(),
        "eligibility":       elig_mod.get("eligibilityCriteria", "").strip(),
        "conditions":        "; ".join(cond_mod.get("conditions", [])),
        "keywords":          "; ".join(cond_mod.get("keywords", [])),
        "interventions":     "; ".join(intv_names),
        "intervention_types":"; ".join(intv_types),
        "primary_outcomes":  "; ".join(primary_measures),
        "sponsor":           safe_get(sponsor_mod, "leadSponsor", "name"),
        "sponsor_class":     safe_get(sponsor_mod, "leadSponsor", "class"),
        "countries":         "; ".join(countries),
    }

def fetch_all_trials(conditions: list, max_trials: int = 400_000):
    all_records = []
    seen_ids = set()

    for condition in conditions:
        print(f"\n📥 Fetching: '{condition}'")
        page_token = None
        condition_count = 0

        while True:
            try:
                data = fetch_trials_batch(condition, page_token)
            except requests.HTTPError as e:
                print(f"  ⚠️  HTTP Error: {e}")
                break
            except Exception as e:
                print(f"  ⚠️  Error: {e}")
                break

            studies = data.get("studies", [])
            if not studies:
                print(f"  ⚠️  No studies returned for '{condition}'")
                break

            for study in studies:
                proto = study.get("protocolSection", {})
                nct_id = proto.get("identificationModule", {}).get("nctId")
                if nct_id and nct_id not in seen_ids:
                    seen_ids.add(nct_id)
                    all_records.append(parse_study(proto))

            condition_count += len(studies)
            print(f"  ✅ Page done — {condition_count} fetched | {len(all_records)} unique total")

            page_token = data.get("nextPageToken")
            if not page_token or len(all_records) >= max_trials:
                break

            time.sleep(0.3)

        if len(all_records) >= max_trials:
            print(f"\n🎯 Reached {max_trials} trial cap.")
            break

    # Save JSONL
    jsonl_path = RAW_DATA_DIR / "trials_raw.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for rec in all_records:
            f.write(json.dumps(rec) + "\n")
    print(f"\n💾 JSONL saved → {jsonl_path}")

    # Save CSV
    df = pd.DataFrame(all_records)
    csv_path = RAW_DATA_DIR / "trials_flat.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8")
    print(f"📊 CSV saved  → {csv_path}  |  shape: {df.shape}")
    return df


if __name__ == "__main__":
    # ── STEP 1: Test the connection first ──────────────────────
    test_data = test_api_connection()
    if not test_data or not test_data.get("studies"):
        print("\n❌ API test failed. Check your internet connection or VPN.")
        exit(1)
    print("\n✅ API working! Starting full pull...\n")

    # ── STEP 2: Full pull ──────────────────────────────────────
    CONDITIONS = [
        "cancer", "diabetes", "cardiovascular disease", "depression",
        "alzheimer", "COVID-19", "hypertension", "obesity", "asthma",
        "HIV", "parkinson", "multiple sclerosis", "rheumatoid arthritis",
        "breast cancer", "lung cancer", "stroke", "kidney disease",
    ]

    df = fetch_all_trials(CONDITIONS, max_trials=400_000)

    # ── STEP 3: Summary ───────────────────────────────────────
    if not df.empty:
        print(f"\n{'='*50}")
        print(f"✅ Done! {len(df)} unique trials collected")
        print(f"\nStatus breakdown:\n{df['status'].value_counts().head(10)}")
        print(f"\nPhase breakdown:\n{df['phase'].value_counts().head(8)}")
        print(f"\nSponsor class:\n{df['sponsor_class'].value_counts()}")
        print(f"\nSample titles:")
        print(df['title'].head(5).to_string())
    else:
        print("❌ DataFrame is empty — check the API test output above.")
        