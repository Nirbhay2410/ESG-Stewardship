"""
Single source of truth for environment and API keys.
Load this first (in main.py) before any other app imports.
"""
import os
from pathlib import Path

# Backend directory (where .env lives) - works when run from project root or backend/
_BACKEND_DIR = Path(__file__).resolve().parent
_ENV_FILE = _BACKEND_DIR / ".env"

_env_loaded = False


def load_env() -> None:
    """Load .env from backend directory. Call this once at app startup (main.py)."""
    global _env_loaded
    if _env_loaded:
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=_ENV_FILE, override=True)
        _env_loaded = True
    except Exception as e:
        print(f"Warning: could not load {_ENV_FILE}: {e}")
        _env_loaded = True  # avoid retry


def _normalize_api_key(raw: str) -> str:
    """Strip quotes, whitespace, newlines, BOM. Return empty string if invalid."""
    if not raw or not isinstance(raw, str):
        return ""
    key = raw.strip()
    key = key.strip('"').strip("'")
    key = key.replace("\r", "").replace("\n", "").replace("\t", "")
    key = key.strip()
    if key.startswith("\ufeff"):
        key = key[1:]
    return key


def get_openrouter_api_key() -> str:
    """Get the OpenRouter API key from environment."""
    load_env()
    return os.getenv("OPENROUTER_API_KEY", "")
