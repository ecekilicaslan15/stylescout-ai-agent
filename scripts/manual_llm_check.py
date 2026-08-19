"""Manual OpenRouter LLM smoke check — run from repo root: python scripts/manual_llm_check.py"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.llm_client import ask_llm

answer = ask_llm(
    "Suggest a casual summer outfit for a computer engineering student.")
print(answer)
