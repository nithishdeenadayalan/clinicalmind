from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=Path("C:/full time/clinicalmind/.env"))

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
FAISS_DIR         = Path("C:/full time/clinicalmind/data/faiss_db")
PROCESSED_DIR     = Path("C:/full time/clinicalmind/data/processed")