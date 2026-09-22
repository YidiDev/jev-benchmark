"""Single place .env is loaded from. Import this before reading any API key
env var, rather than relying on the ambient shell environment (which can
carry stale values from earlier in a session).
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH, override=True)
