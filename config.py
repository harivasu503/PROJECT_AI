import os

# ── Portfolio (Edit your stocks here) ────────────────────────────
PORTFOLIO = {
    "RELIANCE.NS":  {"name": "Reliance Industries", "buy_price": 2400, "qty": 10},
    "TCS.NS":       {"name": "TCS",                  "buy_price": 3500, "qty": 5},
    "INFY.NS":      {"name": "Infosys",              "buy_price": 1450, "qty": 20},
    "HDFCBANK.NS":  {"name": "HDFC Bank",            "buy_price": 1600, "qty": 15},
    "WIPRO.NS":     {"name": "Wipro",                "buy_price": 450,  "qty": 30},
}

# ── Market Themes to Track ────────────────────────────────────────
THEMES = [
    "EV electric vehicle India",
    "defence sector India",
    "renewable energy solar India",
    "banking NBFC credit India",
    "IT sector AI cloud India",
    "infrastructure capex India",
    "pharma healthcare India",
    "PSU public sector divestment India",
]

# ── API Keys (auto-read from GitHub Secrets) ──────────────────────
MARKETAUX_API_KEY = os.environ.get("MARKETAUX_API_KEY", "")
GEMINI_API_KEY    = os.environ.get("GEMINI_API_KEY",    "")

# ── Email Settings ────────────────────────────────────────────────
SENDER_EMAIL    = os.environ.get("SENDER_EMAIL",    "")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "")
RECEIVER_EMAIL  = os.environ.get("RECEIVER_EMAIL",  "")
