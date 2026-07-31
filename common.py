"""
Shared utilities for all asset engines (BBCA, BTC, Gold, ADRO).

Single source of truth for:
- Telegram credentials + sending (one naming convention, everywhere)
- Shared indicator math (RSI, Bollinger %B)
- A reusable yfinance session (Yahoo blocks the default GitHub Actions
  User-Agent intermittently — this reduces silent, unexplained empty fetches)

Import from here in each *_engine.py instead of redefining these.
GitHub Secrets required (same two names for every workflow):
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHAT_ID
"""

import os
import numpy as np
import pandas as pd
import requests

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def send_telegram_msg(text: str) -> bool:
    """Send a Markdown-formatted message to the configured Telegram chat.
    Returns True on success, False otherwise (never raises)."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Telegram credentials missing (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID).")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code == 200:
            print("✅ Alert sent successfully.")
            return True
        print(f"❌ Failed to send alert: {resp.status_code} {resp.text}")
        return False
    except requests.RequestException as e:
        print(f"❌ Telegram request failed: {e}")
        return False


def notify_failure(engine_name: str, error: Exception) -> None:
    """Call this in an except block around data fetching. A silent print()
    means nobody ever finds out the checker itself is broken — this makes
    sure a broken engine still pings you instead of going dark."""
    send_telegram_msg(f"⚠️ *{engine_name} engine failed to run*\n`{error}`")


def get_yf_session() -> requests.Session:
    """yfinance calls from GitHub-hosted runners get rate-limited/blocked by
    Yahoo more often with the default requests User-Agent. Pass this session
    into yf.download(..., session=get_yf_session())."""
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    return session


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """RSI, guarded against the inf/NaN that a flat run of prices produces
    when the rolling average loss hits zero."""
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.replace([np.inf, -np.inf], 100.0)


def compute_bollinger_pctb(close: pd.Series, window: int = 20, num_std: float = 2) -> pd.Series:
    """%B: where price sits within its Bollinger Band (0 = lower band, 1 = upper band)."""
    ma = close.rolling(window).mean()
    std = close.rolling(window).std()
    upper = ma + num_std * std
    lower = ma - num_std * std
    return (close - lower) / (upper - lower)


def flatten_yf_columns(df: pd.DataFrame) -> pd.DataFrame:
    """yfinance sometimes returns a MultiIndex column frame for a single
    ticker depending on call shape — this normalizes it back to flat columns."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    return df
