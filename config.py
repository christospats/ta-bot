import os
from dotenv import load_dotenv

load_dotenv()

# ── Alpaca ──────────────────────────────────────────────
ALPACA_API_KEY    = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_BASE_URL   = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

# ── Ollama ──────────────────────────────────────────────
OLLAMA_MODEL      = os.getenv("OLLAMA_MODEL", "qwen2.5:14b")
OLLAMA_BASE_URL   = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# ── News (Alpaca data feed) ─────────────────────────────
NEWS_LIMIT        = int(os.getenv("NEWS_LIMIT", "5"))

# ── Chart defaults ──────────────────────────────────────
DEFAULT_TIMEFRAME = os.getenv("DEFAULT_TIMEFRAME", "1M")   # 1D 1W 1M 3M 1Y
CHART_WIDTH       = int(os.getenv("CHART_WIDTH", "80"))
CHART_HEIGHT      = int(os.getenv("CHART_HEIGHT", "20"))