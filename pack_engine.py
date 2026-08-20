import yfinance as yf
import pandas as pd

from common import send_telegram_msg, notify_failure, get_yf_session, compute_rsi, compute_bollinger_pctb, flatten_yf_columns


def run_pack_engine():
    print("🔍 Fetching market data for PACK.JK and USD/IDR...")
    session = get_yf_session()
    try:
        df = flatten_yf_columns(yf.download("PACK.JK", period="2y", progress=False, session=session))
        fx_df = flatten_yf_columns(yf.download("IDR=X", period="1y", progress=False, session=session))
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        notify_failure("PACK", e)
        return

    clean_df = df.dropna()
    clean_fx = fx_df.dropna()

    if clean_df.empty or clean_fx.empty:
        print("⚠️ Incomplete dataset. Exiting run.")
        notify_failure("PACK", Exception("Empty dataset from yfinance (PACK.JK or IDR=X)"))
        return

    # --- INDICATOR CALCULATIONS ---
    clean_df["MA50"] = clean_df["Close"].rolling(50).mean()
    clean_df["MA200"] = clean_df["Close"].rolling(200).mean()
    clean_df["pct_vs_200ma"] = (clean_df["Close"] / clean_df["MA200"] - 1) * 100
    clean_df["RSI14"] = compute_rsi(clean_df["Close"])
    clean_df["BB_pctB"] = compute_bollinger_pctb(clean_df["Close"])

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

    # 5. FX Overlay (Inverted for PACK: Strong IDR lowers manufacturing costs)
    if latest_fx["Close"] < latest_fx["MA50"]:
        buy_count += 1
    else:
        sell_count += 1

    # --- DECISION BLOCK ---
    if buy_count >= 3:
        verdict = "🟢 PACK BUY ZONE"
        alert_body = f"PACK is showing structural value with {buy_count}/5 buy signals aligned."
    elif sell_count >= 3:
        verdict = "🔴 PACK SELL ZONE"
        alert_body = f"PACK is technically overextended with {sell_count}/5 sell signals aligned."
    else:
        print(f"⚪ Market state is NEUTRAL ({buy_count} Buy / {sell_count} Sell). No Telegram alert pushed.")
        return

    message = (
        f"🚨 *PACK MARKET REGIME ALERT* 🚨\n\n"
        f"*Verdict:* {verdict}\n"
        f"*Price:* Rp{latest['Close']:,.0f}\n"
        f"*% vs 200 DMA:* {latest['pct_vs_200ma']:+.2f}%\n"
        f"*RSI (14):* {latest['RSI14']:.1f}\n\n"
        f"_{alert_body}_"
    )

    send_telegram_msg(message)


if __name__ == "__main__":
    run_pack_engine()
