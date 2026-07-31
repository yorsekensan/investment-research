import numpy as np
import yfinance as yf
import pandas as pd

from common import send_telegram_msg, notify_failure, get_yf_session, compute_rsi, compute_bollinger_pctb, flatten_yf_columns


def run_gold_engine():
    print("🔍 Fetching market data for GC=F...")
    session = get_yf_session()
    try:
        df = flatten_yf_columns(yf.download("GC=F", period="2y", progress=False, session=session))
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        notify_failure("Gold", e)
        return

    clean_df = df.dropna()
    if clean_df.empty:
        print("⚠️ Incomplete dataset. Exiting run.")
        notify_failure("Gold", Exception("Empty dataset from yfinance (GC=F)"))
        return

    clean_df["MA50"] = clean_df["Close"].rolling(50).mean()
    clean_df["MA200"] = clean_df["Close"].rolling(200).mean()
    clean_df["pct_vs_200ma"] = (clean_df["Close"] / clean_df["MA200"] - 1) * 100
    clean_df["RSI14"] = compute_rsi(clean_df["Close"])
    clean_df["BB_pctB"] = compute_bollinger_pctb(clean_df["Close"])

    clean_df["EMA13"] = clean_df["Close"].ewm(span=13, adjust=False).mean()
    clean_df["EMA21"] = clean_df["Close"].ewm(span=21, adjust=False).mean()
    clean_df["MACD"] = clean_df["EMA13"] - clean_df["EMA21"]
    clean_df["MACD_Signal"] = clean_df["MACD"].ewm(span=9, adjust=False).mean()

    clean_df["Direction"] = np.sign(clean_df["Close"].diff())
    clean_df["OBV"] = (clean_df["Direction"] * clean_df["Volume"]).fillna(0).cumsum()
    clean_df["OBV_MA50"] = clean_df["OBV"].rolling(50).mean()

    latest = clean_df.dropna().iloc[-1]

    buy_count, sell_count = 0, 0

    if latest["MA50"] > latest["MA200"]: buy_count += 1
    else: sell_count += 1

    if latest["pct_vs_200ma"] <= -10: buy_count += 1
    elif latest["pct_vs_200ma"] >= 10: sell_count += 1

    if latest["RSI14"] <= 30: buy_count += 1
    elif latest["RSI14"] >= 70: sell_count += 1

    if latest["BB_pctB"] <= 0: buy_count += 1
    elif latest["BB_pctB"] >= 1: sell_count += 1

    if latest["MACD"] > latest["MACD_Signal"]: buy_count += 1
    else: sell_count += 1

    if latest["OBV"] > latest["OBV_MA50"]: buy_count += 1
    else: sell_count += 1

    if buy_count >= 4:
        verdict = "🟢 MACRO BUY ZONE"
        alert_body = f"Gold is showing structural accumulation with {buy_count}/6 buy signals aligned."
    elif sell_count >= 4:
        verdict = "🔴 MACRO SELL ZONE"
        alert_body = f"Gold is technically overextended with {sell_count}/6 sell signals aligned."
    else:
        print(f"⚪ Market state is NEUTRAL ({buy_count} Buy / {sell_count} Sell). No Telegram alert pushed.")
        return

    message = (
        f"🚨 *GOLD REGIME ALERT* 🚨\n\n"
        f"*Verdict:* {verdict}\n"
        f"*Price:* ${latest['Close']:,.2f}\n"
        f"*% vs 200 DMA:* {latest['pct_vs_200ma']:+.2f}%\n"
        f"*RSI (14):* {latest['RSI14']:.1f}\n\n"
        f"_{alert_body}_"
    )
    send_telegram_msg(message)


if __name__ == "__main__":
    run_gold_engine()
