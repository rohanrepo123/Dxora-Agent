"""Small configuration module shared by the application services."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load a local .env from the project root. On Render, environment variables
# configured in the dashboard take precedence over this file.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

GROQ_MODEL = "openai/gpt-oss-120b"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
METRICS_FILE = PROJECT_ROOT / "metrics.csv"

