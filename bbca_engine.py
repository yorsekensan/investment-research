import yfinance as yf
import pandas as pd

from common import send_telegram_msg, notify_failure, get_yf_session, compute_rsi, compute_bollinger_pctb, flatten_yf_columns


def evaluate_bbca():
    session = get_yf_session()

    try:
        df = flatten_yf_columns(yf.download("BBCA.JK", period="2y", progress=False, session=session))
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        notify_failure("BBCA", e)
        return

    if df.empty:
        print("Failed to fetch BBCA data.")
        notify_failure("BBCA", Exception("Empty dataset from yfinance (BBCA.JK)"))
        return

    df["MA50"] = df["Close"].rolling(50).mean()
    df["MA200"] = df["Close"].rolling(200).mean()
    df["pct_vs_200ma"] = (df["Close"] / df["MA200"] - 1) * 100
    df["RSI14"] = compute_rsi(df["Close"])
    df["BB_pctB"] = compute_bollinger_pctb(df["Close"])

    latest = df.dropna().iloc[-1]

    buy_count, sell_count = 0, 0

    # 1. Trend 50 vs 200
    if latest["MA50"] > latest["MA200"]:
        buy_count += 1
    else:
        sell_count += 1

    # 2. % vs 200 DMA
    if latest["pct_vs_200ma"] <= -5:
        buy_count += 1
    elif latest["pct_vs_200ma"] >= 10:
        sell_count += 1

    # 3. RSI (14)
    if latest["RSI14"] <= 35:
        buy_count += 1
    elif latest["RSI14"] >= 70:
        sell_count += 1

    # 4. Bollinger %B
    if latest["BB_pctB"] <= 0:
        buy_count += 1
    elif latest["BB_pctB"] >= 1:
        sell_count += 1

    # Score calculation: 3+ flags required
    if buy_count >= 3:
        verdict = "STRONG BUY ZONE"
        emoji = "🟢"
    elif sell_count >= 3:
        verdict = "STRONG SELL ZONE"
        emoji = "🔴"
    else:
        verdict = "NEUTRAL REGIME"
        emoji = "⚪"

    if verdict != "NEUTRAL REGIME":
        msg = (
            f"{emoji} *Bank Central Asia (BBCA.JK)*\n"
            f"Verdict: *{verdict}*\n\n"
            f"• Price: Rp{latest['Close']:,.0f}\n"
            f"• Trend: {'BULLISH' if latest['MA50'] > latest['MA200'] else 'BEARISH'}\n"
            f"• % vs 200DMA: {latest['pct_vs_200ma']:+.2f}%\n"
            f"• RSI (14): {latest['RSI14']:.1f}\n"
            f"• Bollinger %B: {latest['BB_pctB']:.2f}"
        )
        send_telegram_msg(msg)
        print("BBCA alert triggered and sent.")
    else:
        print("BBCA regime is neutral; no alert sent.")


if __name__ == "__main__":
    evaluate_bbca()
