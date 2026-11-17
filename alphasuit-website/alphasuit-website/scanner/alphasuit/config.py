"""Central configuration. Everything sensitive comes from environment variables / .env"""
import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", ROOT / "data"))


def _load_dotenv():
    f = ROOT / ".env"
    if not f.exists():
        return
    for line in f.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()
DATA_DIR.mkdir(parents=True, exist_ok=True)


def env(key, default=None):
    return os.environ.get(key, default)


def _secret_key():
    k = env("SECRET_KEY")
    if k:
        return k
    f = DATA_DIR / ".secret_key"
    if f.exists():
        return f.read_text().strip()
    k = secrets.token_hex(32)
    f.write_text(k)
    return k


class Config:
    BRAND = "Alphasuit"
    TAGLINE = "Institutional-grade pattern scanner for Indian stocks & crypto"
    SECRET_KEY = _secret_key()
    PUBLIC_URL = env("PUBLIC_URL", "http://localhost:8000").rstrip("/")
    DB_PATH = env("DB_PATH", str(DATA_DIR / "alphasuit.db"))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = PUBLIC_URL.startswith("https")
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 30

    # --- Free mode: everything open to everyone, no payments (set FREE_MODE=0 to bring back paid plans) ---
    FREE_MODE = env("FREE_MODE", "1") == "1"

    # --- Show entry / stop / target levels? 0 = pure screener (pattern, status, score only) ---
    SHOW_LEVELS = env("SHOW_LEVELS", "0") == "1"

    # --- Admin -------------------------------------------------------------
    ADMIN_PATH = "/" + env("ADMIN_PATH", "admin").strip("/")
    ADMIN_EMAIL = env("ADMIN_EMAIL", "").lower()
    ADMIN_PASSWORD = env("ADMIN_PASSWORD", "")

    # --- Pricing (INR, tax-inclusive) -----------------------------------------
    PRICES = {
        ("stocks", "monthly"): 499,
        ("stocks", "yearly"): 4999,
        ("crypto", "monthly"): 999,
        ("crypto", "yearly"): 9999,
    }
    PERIOD_DAYS = {"monthly": 30, "yearly": 365}
    PRODUCTS = {
        "stocks": "Indian Stocks (NSE + BSE)",
        "crypto": "Crypto",
    }

    # --- Payments --------------------------------------------------------------
    RAZORPAY_KEY_ID = env("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET = env("RAZORPAY_KEY_SECRET", "")
    RAZORPAY_WEBHOOK_SECRET = env("RAZORPAY_WEBHOOK_SECRET", "")
    # Your UPI ID lives ONLY here (server side). It is never rendered into any page.
    UPI_VPA = env("UPI_VPA", "")
    UPI_PAYEE_NAME = env("UPI_PAYEE_NAME", "Alphasuit")

    # --- Mail (password reset) ------------------------------------------------
    SMTP_HOST = env("SMTP_HOST", "")
    SMTP_PORT = int(env("SMTP_PORT", "587"))
    SMTP_USER = env("SMTP_USER", "")
    SMTP_PASSWORD = env("SMTP_PASSWORD", "")
    MAIL_FROM = env("MAIL_FROM", "Alphasuit <no-reply@alphasuit.local>")

    # --- Scanner ---------------------------------------------------------------
    RUN_SCHEDULER = env("RUN_SCHEDULER", "1") == "1"
    SCAN_WORKERS = int(env("SCAN_WORKERS", "8"))
    # auto = Google Sheets if SHEETS_CSV_URLS is set, else NSE files; chain: sheets -> nse -> yahoo.  Or force: sheets | nse | yahoo
    STOCK_DATA_SOURCE = env("STOCK_DATA_SOURCE", "auto")
    SHEETS_CSV_URLS = env("SHEETS_CSV_URLS", "")  # comma-separated "Publish to web" CSV links, one per sheet tab
    NSE_UNIVERSE = env("NSE_UNIVERSE", "all")  # all | nifty500
    BSE_ENABLED = env("BSE_ENABLED", "1") == "1"
    CRYPTO_TOP_N = int(env("CRYPTO_TOP_N", "150"))
    CRYPTO_API_BASE = env("CRYPTO_API_BASE", "https://data-api.binance.vision").rstrip("/")
    CRYPTO_TIMEFRAMES = [t.strip() for t in env("CRYPTO_TIMEFRAMES", "1d,4h").split(",") if t.strip()]
    MIN_TURNOVER_INR = float(env("MIN_TURNOVER_INR", "10000000"))  # avg daily value, Rs 1 crore
    MIN_PRICE_INR = float(env("MIN_PRICE_INR", "10"))
    MIN_TURNOVER_USD = float(env("MIN_TURNOVER_USD", "1000000"))
    MIN_SCORE = int(env("MIN_SCORE", "70"))
    STOCK_SCAN_TIME_IST = env("STOCK_SCAN_TIME_IST", "22:00")   # once per trading night (Mon-Fri), after the close
    CRYPTO_SCAN_TIME_IST = env("CRYPTO_SCAN_TIME_IST", "22:00")  # once per day (empty = use CRYPTO_SCAN_EVERY_HOURS)
    CRYPTO_SCAN_EVERY_HOURS = int(env("CRYPTO_SCAN_EVERY_HOURS", "24"))
    FREE_PREVIEW_ROWS = int(env("FREE_PREVIEW_ROWS", "3"))
