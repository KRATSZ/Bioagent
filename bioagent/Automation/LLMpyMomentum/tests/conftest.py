import os
import sys
from pathlib import Path


# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Load .env if present to allow LLM live tests
try:
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=ROOT / ".env")
except Exception:
    pass




