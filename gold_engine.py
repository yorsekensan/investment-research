import os
import requests
import yfinance as yf
import pandas as pd
import numpy as np

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_alert(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Telegram credentials missing.")
        return
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("✅ Alert sent successfully.")
    else:
        print(f"❌ Failed to send alert: {response.text}")

def run_gold_engine():
    print("🔍 Fetching market data for GC=F...")
    try:
        df = yf.download("GC=F", period="2y", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        return

    clean_df = df.dropna()
    if clean_df.empty:
        print("⚠️ Incomplete dataset. Exiting run.")
        return

    clean_df["MA50"] = clean_df["Close"].rolling(50).mean()
    clean_df["MA200"] = clean_df["Close"].rolling(200).mean()
    clean_df["pct_vs_200ma"] = (clean_df["Close"] / clean_df["MA200"] - 1) * 100

    delta = clean_df["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    clean_df["RSI14"] = 100 - (100 / (1 + rs))

    ma20 = clean_df["Close"].rolling(20).mean()
    std20 = clean_df["Close"].rolling(20).std()
    clean_df["Upper_BB"] = ma20 + (2 * std20)
    clean_df["Lower_BB"] = ma20 - (2 * std20)
    clean_df["BB_pctB"] = (clean_df["Close"] - clean_df["Lower_BB"]) / (clean_df["Upper_BB"] - clean_df["Lower_BB"])

    clean_df["EMA13"] = clean_df["Close"].ewm(span=13, adjust=False).mean()
    clean_df["EMA21"] = clean_df["Close"].ewm(span=21, adjust=False).mean()
    clean_df["MACD"] = clean_df["EMA13"] - clean_df["EMA21"]
    clean_df["MACD_Signal"] = clean_df["MACD"].ewm(span=9, adjust=False).mean()

    clean_df['Direction'] = np.sign(clean_df['Close'].diff())
    clean_df['OBV'] = (clean_df['Direction'] * clean_df['Volume']).fillna(0).cumsum()
    clean_df['OBV_MA50'] = clean_df['OBV'].rolling(50).mean()

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
    send_telegram_alert(message)

if __name__ == "__main__":
    run_gold_engine()
