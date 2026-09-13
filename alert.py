import os
import json
import requests
import yfinance as yf
import pandas as pd
import numpy as np

# 1. SETUP & CONFIGURATION
STATE_FILE = "state.json"
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def fetch_data():
    tickers = ["BTC-USD", "GC=F", "BBCA.JK", "ADRO.JK", "PACK.JK", "FORU.JK", "DOOH.JK", "DX-Y.NYB", "^GSPC", "^TNX", "^JKSE", "IDR=X"]
    # Tarik semua data secara utuh, biarkan bentuk MultiIndex agar Volume dan Close ikut terbawa
    data = yf.download(tickers, period="1y", progress=False)
    return data

def calculate_asset_score(asset_ticker, data, asset_type):
    # Ekstrak Close dan Volume dari struktur MultiIndex
    if isinstance(data.columns, pd.MultiIndex) and 'Close' in data.columns.levels[0]:
        s_close = data['Close'].get(asset_ticker, pd.Series()).apply(pd.to_numeric, errors='coerce').dropna()
        s_vol = data['Volume'].get(asset_ticker, pd.Series()).apply(pd.to_numeric, errors='coerce').dropna() if 'Volume' in data.columns.levels[0] else pd.Series(dtype=float)
    else:
        return "N/A", "0%", "⚪ Data Error"
        
    if s_close.empty or len(s_close) < 20: 
        return "N/A", "0%", "⚪ Data Error"
        
    df = pd.DataFrame({'Close': s_close, 'Volume': s_vol})
    df['SMA_50'] = df['Close'].rolling(50).mean()
    df['SMA_200'] = df['Close'].rolling(200).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss.replace(0, 1e-10))))
    
    exp1 = df['Close'].ewm(span=13, adjust=False).mean()
    exp2 = df['Close'].ewm(span=21, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    cur = df.iloc[-1]
    
    s_dxy = data['Close'].get('DX-Y.NYB', pd.Series()).apply(pd.to_numeric, errors='coerce').dropna() if 'Close' in data.columns.levels[0] else pd.Series()
    s_tnx = data['Close'].get('^TNX', pd.Series()).apply(pd.to_numeric, errors='coerce').dropna() if 'Close' in data.columns.levels[0] else pd.Series()
    s_ihsg = data['Close'].get('^JKSE', pd.Series()).apply(pd.to_numeric, errors='coerce').dropna() if 'Close' in data.columns.levels[0] else pd.Series()
    s_spx = data['Close'].get('^GSPC', pd.Series()).apply(pd.to_numeric, errors='coerce').dropna() if 'Close' in data.columns.levels[0] else pd.Series()
    s_idr = data['Close'].get('IDR=X', pd.Series()).apply(pd.to_numeric, errors='coerce').dropna() if 'Close' in data.columns.levels[0] else pd.Series()
    
    price_str = f"Rp {cur['Close']:,.0f}" if asset_type not in ["btc", "gold"] else f"${cur['Close']:,.2f}"

    # ==========================================
    # LOGIKA SKORING STANDAR
    # ==========================================
    if asset_type not in ["foru", "dooh"]:
        score = 0
        is_bull_regime = pd.notna(cur.get('SMA_200')) and cur['Close'] > cur['SMA_200']

        if is_bull_regime: score += 30
        if pd.notna(cur.get('SMA_50')) and cur['Close'] > cur['SMA_50']: score += 10
        if pd.notna(cur.get('RSI')) and cur['RSI'] < 40 and is_bull_regime: score += 5
        if pd.notna(cur.get('MACD')) and pd.notna(cur.get('Signal')) and cur['MACD'] > cur['Signal']: score += 10
        
        if asset_type == "btc":
            if not s_dxy.empty and len(s_dxy) >= 50 and s_dxy.iloc[-1] < s_dxy.rolling(50).mean().iloc[-1]: score += 25
            if not s_spx.empty and len(df) >= 20 and len(s_spx) >= 20 and ((df['Close'].iloc[-1] - df['Close'].iloc[-20]) / df['Close'].iloc[-20]) > ((s_spx.iloc[-1] - s_spx.iloc[-20]) / s_spx.iloc[-20]): score += 20
        elif asset_type == "gold":
            if not s_dxy.empty and len(s_dxy) >= 50 and s_dxy.iloc[-1] < s_dxy.rolling(50).mean().iloc[-1]: score += 25
            if not s_tnx.empty and len(s_tnx) >= 50 and s_tnx.iloc[-1] < s_tnx.rolling(50).mean().iloc[-1]: score += 20
        elif asset_type == "bbca":
            if not s_tnx.empty and len(s_tnx) >= 50 and s_tnx.iloc[-1] < s_tnx.rolling(50).mean().iloc[-1]: score += 25
            if not s_ihsg.empty and len(df) >= 20 and len(s_ihsg) >= 20 and ((df['Close'].iloc[-1] - df['Close'].iloc[-20]) / df['Close'].iloc[-20]) > ((s_ihsg.iloc[-1] - s_ihsg.iloc[-20]) / s_ihsg.iloc[-20]): score += 20
        elif asset_type == "adro":
            if not s_idr.empty and len(s_idr) >= 50 and s_idr.iloc[-1] > s_idr.rolling(50).mean().iloc[-1]: score += 25
            if not s_ihsg.empty and len(df) >= 20 and len(s_ihsg) >= 20 and ((df['Close'].iloc[-1] - df['Close'].iloc[-20]) / df['Close'].iloc[-20]) > ((s_ihsg.iloc[-1] - s_ihsg.iloc[-20]) / s_ihsg.iloc[-20]): score += 20
        elif asset_type == "pack":
            if not s_idr.empty and len(s_idr) >= 50 and s_idr.iloc[-1] > s_idr.rolling(50).mean().iloc[-1]: score += 25 # PACK Direct IDR
            if not s_ihsg.empty and len(df) >= 20 and len(s_ihsg) >= 20 and ((df['Close'].iloc[-1] - df['Close'].iloc[-20]) / df['Close'].iloc[-20]) > ((s_ihsg.iloc[-1] - s_ihsg.iloc[-20]) / s_ihsg.iloc[-20]): score += 20

    # ==========================================
    # LOGIKA SKORING TRANSISIONAL (FORU & DOOH)
    # ==========================================
    else:
        score = 0
        
        obv = np.where(df['Close'] > df['Close'].shift(1), df['Volume'], np.where(df['Close'] < df['Close'].shift(1), -df['Volume'], 0))
        df['OBV'] = pd.Series(obv, index=df.index).cumsum()
        
        if not s_ihsg.empty and len(df) >= 20 and len(s_ihsg) >= 20 and ((df['Close'].iloc[-1] - df['Close'].iloc[-20]) / df['Close'].iloc[-20]) > ((s_ihsg.iloc[-1] - s_ihsg.iloc[-20]) / s_ihsg.iloc[-20]): score += 20
        if cur['Close'] > cur['SMA_50']: score += 15
        if cur['MACD'] > cur['Signal']: score += 15
        if cur['RSI'] < 40 and cur['Close'] > cur['SMA_50']: score += 5
        if not df['OBV'].empty and len(df) >= 20 and df['OBV'].iloc[-1] > df['OBV'].rolling(20).mean().iloc[-1]: score += 20
        
        if asset_type == "foru":
            if not s_idr.empty and len(s_idr) >= 50 and s_idr.iloc[-1] > s_idr.rolling(50).mean().iloc[-1]: score += 25 # Direct IDR
        elif asset_type == "dooh":
            if not s_tnx.empty and len(s_tnx) >= 50 and s_tnx.iloc[-1] < s_tnx.rolling(50).mean().iloc[-1]: score += 25 # Inverse TNX
            
    if score >= 70: regime = "🟢 Macro Bull Engine"
    elif score <= 30: regime = "🔴 Severe Bear Market"
    else: regime = "⚪ Neutral / Chop"
        
    return price_str, f"{score}%", regime

# 2. STATE TRACKING & ALERT EXECUTION
def main():
    print("Fetching market data...")
    data = fetch_data()
    
    # Menambahkan FORU dan DOOH ke dalam antrean pantauan
    assets = [
        {"ticker": "BTC-USD", "type": "btc", "name": "Bitcoin"},
        {"ticker": "BBCA.JK", "type": "bbca", "name": "BBCA"},
        {"ticker": "ADRO.JK", "type": "adro", "name": "ADRO"},
        {"ticker": "PACK.JK", "type": "pack", "name": "PACK"},
        {"ticker": "GC=F", "type": "gold", "name": "Gold"},
        {"ticker": "FORU.JK", "type": "foru", "name": "FORU"},
        {"ticker": "DOOH.JK", "type": "dooh", "name": "DOOH"}
    ]
    
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            old_state = json.load(f)
    else:
        old_state = {}
        
    new_state = {}
    portfolio_summary = []
    any_shifts = False
    
    for item in assets:
        ticker = item["ticker"]
        name = item["name"]
        
        price, score_str, regime = calculate_asset_score(ticker, data, item["type"])
        
        if price == "N/A":
            print(f"Skipping {ticker} due to data error.")
            continue
            
        new_state[ticker] = regime
        old_state_val = old_state.get(ticker, "Initialization")
        
        if old_state_val == "Initialization":
            any_shifts = True
            portfolio_summary.append(
                f"⚡ <b>{name}</b>: {regime}\n"
                f"   <i>(Baseline Locked)</i>\n"
                f"   Price: {price} | Score: {score_str}"
            )
        elif old_state_val != regime:
            any_shifts = True
            portfolio_summary.append(
                f"⚡ <b>{name}</b>: {regime}\n"
                f"   <i>(Shifted from: {old_state_val})</i>\n"
                f"   Price: {price} | Score: {score_str}"
            )
        else:
            portfolio_summary.append(
                f"🔹 <b>{name}</b>: {regime}\n"
                f"   Price: {price} | Score: {score_str}"
            )
            
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
            
    with open(STATE_FILE, "w") as f:
        json.dump(new_state, f)

if __name__ == "__main__":
    main()
