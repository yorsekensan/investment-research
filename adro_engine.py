import os
import requests
import yfinance as yf
import pandas as pd

# Environment variables from GitHub Secrets
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_alert(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Telegram credentials missing.")
        return
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("✅ Alert sent successfully.")
    else:
        print(f"❌ Failed to send alert: {response.text}")

def run_adro_engine():
    print("🔍 Fetching market data for ADRO.JK and USD/IDR...")
    try:
        df = yf.download("ADRO.JK", period="2y", progress=False)
        fx_df = yf.download("IDR=X", period="1y", progress=False)

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        if isinstance(fx_df.columns, pd.MultiIndex):
            fx_df.columns = fx_df.columns.droplevel(1)
            
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        return

    clean_df = df.dropna()
    clean_fx = fx_df.dropna()

    if clean_df.empty or clean_fx.empty:
        print("⚠️ Incomplete dataset. Exiting run.")
        return

    # --- INDICATOR CALCULATIONS ---
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

    clean_fx["MA50"] = clean_fx["Close"].rolling(50).mean()

    latest = clean_df.dropna().iloc[-1]
    latest_fx = clean_fx.dropna().iloc[-1]

    # --- SCORING REGIME LOGIC ---
    buy_count, sell_count = 0, 0

    # 1. Trend
    if latest["MA50"] > latest["MA200"]:
        buy_count += 1
    else:
        sell_count += 1

    # 2. 200 DMA Stretch
    if latest["pct_vs_200ma"] <= -15:
        buy_count += 1
    elif latest["pct_vs_200ma"] >= 15:
        sell_count += 1

    # 3. RSI
    if latest["RSI14"] <= 35:
        buy_count += 1
    elif latest["RSI14"] >= 70:
        sell_count += 1

    # 4. Bollinger %B
    if latest["BB_pctB"] <= 0:
        buy_count += 1
    elif latest["BB_pctB"] >= 1:
        sell_count += 1

    # 5. FX Overlay
    if latest_fx["Close"] > latest_fx["MA50"]:
        buy_count += 1
    else:
        sell_count += 1

    # --- DECISION BLOCK ---
    if buy_count >= 3:
        verdict = "🟢 CYCLICAL BUY ZONE"
        alert_body = f"ADRO is showing deep cyclical value with {buy_count}/5 buy signals aligned."
    elif sell_count >= 3:
        verdict = "🔴 CYCLICAL SELL ZONE"
        alert_body = f"ADRO is technically overextended with {sell_count}/5 sell signals aligned."
    else:
        print(f"⚪ Market state is NEUTRAL ({buy_count} Buy / {sell_count} Sell). No Telegram alert pushed.")
        return

    # Construct Message
    message = (
        f"🚨 *ADRO MARKET REGIME ALERT* 🚨\n\n"
        f"*Verdict:* {verdict}\n"
        f"*Price:* Rp{latest['Close']:,.0f}\n"
        f"*% vs 200 DMA:* {latest['pct_vs_200ma']:+.2f}%\n"
        f"*RSI (14):* {latest['RSI14']:.1f}\n\n"
        f"_{alert_body}_"
    )

    send_telegram_alert(message)

if __name__ == "__main__":
    run_adro_engine()
