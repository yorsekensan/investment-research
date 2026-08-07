import os
import json
import requests
import yfinance as yf
import pandas as pd

# 1. SETUP & CONFIGURATION
STATE_FILE = "state.json"
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def fetch_data():
    tickers = ["BTC-USD", "GC=F", "BBCA.JK", "ADRO.JK", "DX-Y.NYB", "^GSPC", "^TNX", "^JKSE", "IDR=X"]
    df_raw = yf.download(tickers, period="max", progress=False)
    
    if isinstance(df_raw.columns, pd.MultiIndex):
        if 'Close' in df_raw.columns.levels[0]:
            return df_raw['Close']
        else:
            return df_raw.xs('Close', axis=1, level=0, drop_level=True)
    return df_raw

def calculate_asset_score(asset_ticker, data, asset_type):
    if asset_ticker not in data.columns: return "N/A", "0%", "⚪ Data Error"
    
    s_asset = pd.Series(data[asset_ticker]).apply(pd.to_numeric, errors='coerce').dropna()
    if s_asset.empty or len(s_asset) < 20: return "N/A", "0%", "⚪ Data Error"
        
    df = pd.DataFrame({'Close': s_asset})
    df['SMA_50'] = df['Close'].rolling(50).mean()
    df['SMA_200'] = df['Close'].rolling(200).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    
    exp1 = df['Close'].ewm(span=13, adjust=False).mean()
    exp2 = df['Close'].ewm(span=21, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    cur = df.iloc[-1]
    score = 0
    is_bull_regime = pd.notna(cur.get('SMA_200')) and cur['Close'] > cur['SMA_200']

    if is_bull_regime: score += 30
    if pd.notna(cur.get('SMA_50')) and cur['Close'] > cur['SMA_50']: score += 10
    if pd.notna(cur.get('RSI')) and cur['RSI'] < 40 and is_bull_regime: score += 5 
    if pd.notna(cur.get('MACD')) and pd.notna(cur.get('Signal')) and cur['MACD'] > cur['Signal']: score += 10
    
    s_dxy = pd.Series(data.get('DX-Y.NYB', pd.Series(dtype=float))).apply(pd.to_numeric, errors='coerce').dropna()
    s_tnx = pd.Series(data.get('^TNX', pd.Series(dtype=float))).apply(pd.to_numeric, errors='coerce').dropna()
    s_ihsg = pd.Series(data.get('^JKSE', pd.Series(dtype=float))).apply(pd.to_numeric, errors='coerce').dropna()
    s_spx = pd.Series(data.get('^GSPC', pd.Series(dtype=float))).apply(pd.to_numeric, errors='coerce').dropna()
    s_idr = pd.Series(data.get('IDR=X', pd.Series(dtype=float))).apply(pd.to_numeric, errors='coerce').dropna()
    
    if asset_type == "btc":
        if not s_dxy.empty and len(s_dxy) >= 50 and s_dxy.iloc[-1] < s_dxy.rolling(50).mean().iloc[-1]: score += 25
        if not s_spx.empty and len(df) >= 20 and len(s_spx) >= 20 and ((df['Close'].iloc[-1] - df['Close'].iloc[-20]) / df['Close'].iloc[-20]) > ((s_spx.iloc[-1] - s_spx.iloc[-20]) / s_spx.iloc[-20]): score += 20
        price_str = f"${cur['Close']:,.2f}"

    elif asset_type == "gold":
        if not s_dxy.empty and len(s_dxy) >= 50 and s_dxy.iloc[-1] < s_dxy.rolling(50).mean().iloc[-1]: score += 25
        if not s_tnx.empty and len(s_tnx) >= 50 and s_tnx.iloc[-1] < s_tnx.rolling(50).mean().iloc[-1]: score += 20
        price_str = f"${cur['Close']:,.2f}"

    elif asset_type == "bbca":
        if not s_tnx.empty and len(s_tnx) >= 50 and s_tnx.iloc[-1] < s_tnx.rolling(50).mean().iloc[-1]: score += 25
        if not s_ihsg.empty and len(df) >= 20 and len(s_ihsg) >= 20 and ((df['Close'].iloc[-1] - df['Close'].iloc[-20]) / df['Close'].iloc[-20]) > ((s_ihsg.iloc[-1] - s_ihsg.iloc[-20]) / s_ihsg.iloc[-20]): score += 20
        price_str = f"Rp {cur['Close']:,.0f}"

    elif asset_type == "adro":
        if not s_idr.empty and len(s_idr) >= 50 and s_idr.iloc[-1] > s_idr.rolling(50).mean().iloc[-1]: score += 25
        if not s_ihsg.empty and len(df) >= 20 and len(s_ihsg) >= 20 and ((df['Close'].iloc[-1] - df['Close'].iloc[-20]) / df['Close'].iloc[-20]) > ((s_ihsg.iloc[-1] - s_ihsg.iloc[-20]) / s_ihsg.iloc[-20]): score += 20
        price_str = f"Rp {cur['Close']:,.0f}"
        
    if score >= 60: regime = "🟢 Macro Bull Engine"
    elif score < 40: regime = "🔴 Severe Bear Market"
    else: regime = "⚪ Neutral / Chop"
        
    return price_str, f"{score}%", regime

# 2. STATE TRACKING & ALERT EXECUTION
def main():
    print("Fetching market data...")
    data = fetch_data()
    assets = [
        {"ticker": "BTC-USD", "type": "btc", "name": "Bitcoin"},
        {"ticker": "BBCA.JK", "type": "bbca", "name": "BBCA"},
        {"ticker": "ADRO.JK", "type": "adro", "name": "ADRO"},
        {"ticker": "GC=F", "type": "gold", "name": "Gold"}
    ]
    
    # Load memory
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            old_state = json.load(f)
    else:
        old_state = {}
        
    new_state = {}
    alerts = []
    
    # Process assets
    for item in assets:
        price, score_str, regime = calculate_asset_score(item["ticker"], data, item["type"])
        new_state[item["ticker"]] = regime
        
        old_regime = old_state.get(item["ticker"], "Initialization")
        
        # Check if the regime flipped
        if old_regime != "Initialization" and old_regime != regime:
            alerts.append(
                f"⚡ <b>MACRO REGIME SHIFT: {item['name']}</b>\n\n"
                f"<b>Previous:</b> {old_regime}\n"
                f"<b>Current:</b> {regime} (Score: {score_str})\n"
                f"<b>Last Price:</b> {price}\n\n"
                f"<i>Check the terminal for detailed factor breakdown.</i>"
            )
            
    # Send Telegram Alerts
    if alerts and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        for alert_msg in alerts:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            payload = {"chat_id": TELEGRAM_CHAT_ID, "text": alert_msg, "parse_mode": "HTML"}
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                print(f"Alert sent for {item['name']}")
            else:
                print(f"Telegram API Error: {response.text}")
    else:
        print("No regime shifts detected today, or missing API keys. Staying silent.")
            
    # Commit new state to memory
    with open(STATE_FILE, "w") as f:
        json.dump(new_state, f)
        
if __name__ == "__main__":
    main()
