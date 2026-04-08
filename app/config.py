import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BACKEND_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BACKEND_DIR / "data" / "modelx.db"

DB_PATH = os.getenv("MODELX_DB_PATH", str(DEFAULT_DB_PATH))
REFRESH_INTERVAL = int(os.getenv("MODELX_REFRESH_INTERVAL", "120"))
FETCH_LIMIT = int(os.getenv("MODELX_FETCH_LIMIT", "20"))
AUTO_REFRESH_DEFAULT = os.getenv("MODELX_AUTO_REFRESH_DEFAULT", "true").lower() == "true"
