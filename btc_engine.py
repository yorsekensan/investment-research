import datetime
import requests
import pandas as pd

from common import send_telegram_msg, notify_failure, compute_rsi, compute_bollinger_pctb


def _fetch_blockchain_chart(chart_name):
    url = f"https://api.blockchain.info/charts/{chart_name}"
    params = {"timespan": "1000d", "format": "json", "sampled": "false"}
    res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=20).json()
    out = pd.DataFrame(res["values"])
    out["date"] = pd.to_datetime(out["x"], unit="s").dt.normalize()
    return out[["date", "y"]]


def get_btc_data():
    price = _fetch_blockchain_chart("market-price").rename(columns={"y": "close"})
    revenue = _fetch_blockchain_chart("miners-revenue").rename(columns={"y": "miner_rev_usd"})

    df = pd.merge(price, revenue, on="date", how="left").sort_values("date").reset_index(drop=True)
    df = df[df["close"] > 0].reset_index(drop=True)

    df["MA200"] = df["close"].rolling(200).mean()
    df["MA111"] = df["close"].rolling(111).mean()
    df["MA350x2"] = df["close"].rolling(350).mean() * 2
    df["pct_vs_200ma"] = (df["close"] / df["MA200"] - 1) * 100
    df["RSI14"] = compute_rsi(df["close"])
    df["BB_pctB"] = compute_bollinger_pctb(df["close"])
    df["puell"] = df["miner_rev_usd"] / df["miner_rev_usd"].rolling(365).mean()
    return df


def get_fng():
    res = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10).json()["data"][0]
    return int(res["value"]), res["value_classification"]


def evaluate_btc():
    try:
        df = get_btc_data()
        fng_val, fng_class = get_fng()
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        notify_failure("BTC", e)
        return

    latest = df.iloc[-1]

    buy_count, sell_count = 0, 0

    # 1. % vs 200DMA
    if latest["pct_vs_200ma"] <= -15: buy_count += 1
    elif latest["pct_vs_200ma"] >= 100: sell_count += 1

    # 2. Puell Multiple
    if latest["puell"] <= 0.5: buy_count += 1
    elif latest["puell"] >= 4.0: sell_count += 1

    # 3. RSI (14)
    if latest["RSI14"] <= 30: buy_count += 1
    elif latest["RSI14"] >= 70: sell_count += 1

    # 4. Bollinger %B
    if latest["BB_pctB"] <= 0: buy_count += 1
    elif latest["BB_pctB"] >= 1: sell_count += 1

    # 5. Fear & Greed
    if fng_val <= 25: buy_count += 1
    elif fng_val >= 75: sell_count += 1

    # 6. Pi Cycle Top
    if latest["MA111"] > latest["MA350x2"]: sell_count += 1

    if sell_count >= 4:
        verdict = "MAJORITY SELL ZONE"
        emoji = "🔴"
    elif buy_count >= 4:
        verdict = "MAJORITY BUY ZONE"
        emoji = "🟢"
    else:
        verdict = "MIXED / NEUTRAL REGIME"
        emoji = "⚪"

    msg = (
        f"{emoji} *Bitcoin (BTC) Macro Regime*\n"
        f"Verdict: *{verdict}*\n"
        f"Signals: {buy_count} Buy | {sell_count} Sell | {6 - buy_count - sell_count} Neutral\n\n"
        f"• Price: ${latest['close']:,.0f}\n"
        f"• % vs 200DMA: {latest['pct_vs_200ma']:+.1f}%\n"
        f"• Puell Multiple: {latest['puell']:.2f}\n"
        f"• RSI (14): {latest['RSI14']:.1f}\n"
        f"• Fear & Greed: {fng_val} ({fng_class})"
    )

    # Throttling: send if actionable, OR at the 00:00 UTC (07:00 WIB) morning heartbeat
    current_utc_hour = datetime.datetime.now(datetime.timezone.utc).hour
    if verdict != "MIXED / NEUTRAL REGIME" or current_utc_hour == 0:
        send_telegram_msg(msg)
        print("BTC notification sent.")
    else:
        print("BTC regime is neutral; skipping non-morning alert.")


if __name__ == "__main__":
    evaluate_btc()
