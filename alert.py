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
    if asset_ticker not in data.columns: 
        return "N/A", "0%", "⚪ Data Error", None
    
    s_asset = pd.Series(data[asset_ticker]).apply(pd.to_numeric, errors='coerce').dropna()
    if s_asset.empty or len(s_asset) < 20: 
        return "N/A", "0%", "⚪ Data Error", None
        
    df = pd.DataFrame({'Close': s_asset})
    df['SMA_50'] = df['Close'].rolling(50).mean()
    df['SMA_200'] = df['Close'].rolling(200).mean()
    
    # RSI Calculation (14-period Wilder/SMA)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, 1e-10)
    df['RSI'] = 100 - (100 / (1 + rs))
    
    exp1 = df['Close'].ewm(span=13, adjust=False).mean()
    exp2 = df['Close'].ewm(span=21, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    cur = df.iloc[-1]
    current_rsi = round(cur['RSI'], 2) if pd.notna(cur.get('RSI')) else None
    
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
        
    return price_str, f"{score}%", regime, current_rsi

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
    portfolio_summary = []
    any_shifts = False
    
    # Process assets loop
    for item in assets:
        ticker = item["ticker"]
        name = item["name"]
        
        price, score_str, regime, current_rsi = calculate_asset_score(ticker, data, item["type"])
        
        if price == "N/A":
            print(f"Skipping {ticker} due to data error.")
            continue
            
        # Keep Value logic for the tracker, but remove messy RSI numbers from the text
        if current_rsi is not None and current_rsi <= 30:
            value_tag = " | 🟢 DEEP VALUE"
        elif current_rsi is not None and current_rsi >= 70:
            value_tag = " | 🔴 OVERBOUGHT"
        else:
            value_tag = ""
            
        # The clean status string saved to memory
        combined_state = f"{regime}{value_tag}"
        new_state[ticker] = combined_state
        
        old_state_val = old_state.get(ticker, "Initialization")
        
        # Check if this specific asset caused the shift
        if old_state_val == "Initialization":
            any_shifts = True
            portfolio_summary.append(
                f"⚡ <b>{name}</b>: {combined_state}\n"
                f"   <i>(Baseline Locked)</i>\n"
                f"   Price: {price} | Score: {score_str}"
            )
        elif old_state_val != combined_state:
            any_shifts = True
            portfolio_summary.append(
                f"⚡ <b>{name}</b>: {combined_state}\n"
                f"   <i>(Shifted from: {old_state_val})</i>\n"
                f"   Price: {price} | Score: {score_str}"
            )
        else:
            # Asset didn't change, just display its current status cleanly
            portfolio_summary.append(
                f"🔹 <b>{name}</b>: {combined_state}\n"
                f"   Price: {price} | Score: {score_str}"
            )
            
    # Send 1 Consolidated Telegram Alert if ANY asset changed
    if any_shifts:
        final_message = "🚨 <b>MACRO PORTFOLIO UPDATE</b>\n\n" + "\n\n".join(portfolio_summary)
        
        if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            payload = {"chat_id": TELEGRAM_CHAT_ID, "text": final_message, "parse_mode": "HTML"}
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                print("Single summary alert sent successfully.")
            else:
                print(f"Telegram API Error: {response.text}")
    else:
        print("No regime shifts detected today. Staying silent.")
            
    # Commit new state to memory file
    with open(STATE_FILE, "w") as f:
        json.dump(new_state, f)

if __name__ == "__main__":
    main()
