import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# ==========================================
# ⚙️ COMMAND CENTER CONFIGURATION
# ==========================================
st.set_page_config(page_title="YS Investment Research | Command Center", page_icon="⚡", layout="wide")

st.title("⚡ YS Investment Research Terminal")
st.write("Institutional-grade quantitative macro tracking across global equities, digital assets, precious metals, and emerging markets.")
st.divider()

# --- 1. BULK DATA FETCHING ---
@st.cache_data(ttl=3600)
def fetch_command_center_data():
    tickers = ["BTC-USD", "GC=F", "BBCA.JK", "ADRO.JK", "PACK.JK", "FORU.JK", "DOOH.JK", "DX-Y.NYB", "^GSPC", "^TNX", "^JKSE", "IDR=X"]
    # Download semua data (termasuk Close dan Volume)
    df_raw = yf.download(tickers, period="max", progress=False)
    return df_raw

try:
    data = fetch_command_center_data()
except Exception as e:
    st.error(f"Failed to fetch live macro data: {e}")
    st.stop()

def calculate_asset_score(asset_ticker, data, asset_type):
    # Ekstrak Close dan Volume dari struktur MultiIndex
    if isinstance(data.columns, pd.MultiIndex) and 'Close' in data.columns.levels[0]:
        s_close = data['Close'].get(asset_ticker, pd.Series()).apply(pd.to_numeric, errors='coerce').dropna()
        s_vol = data['Volume'].get(asset_ticker, pd.Series()).apply(pd.to_numeric, errors='coerce').dropna() if 'Volume' in data.columns.levels[0] else pd.Series(dtype=float)
    else:
        return "N/A", "0%", "⚪ Data Error"
        
    if s_close.empty or len(s_close) < 20: return "N/A", "0%", "⚪ Data Error"
        
    df = pd.DataFrame({'Close': s_close, 'Volume': s_vol})
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
    
    # Ekstrak data Makro (Hanya butuh Close)
    s_dxy = data['Close'].get('DX-Y.NYB', pd.Series()).apply(pd.to_numeric, errors='coerce').dropna()
    s_tnx = data['Close'].get('^TNX', pd.Series()).apply(pd.to_numeric, errors='coerce').dropna()
    s_ihsg = data['Close'].get('^JKSE', pd.Series()).apply(pd.to_numeric, errors='coerce').dropna()
    s_spx = data['Close'].get('^GSPC', pd.Series()).apply(pd.to_numeric, errors='coerce').dropna()
    s_idr = data['Close'].get('IDR=X', pd.Series()).apply(pd.to_numeric, errors='coerce').dropna()
    
    price_str = f"Rp {cur['Close']:,.0f}" if asset_type not in ["btc", "gold"] else f"${cur['Close']:,.2f}"

    # ==========================================
    # LOGIKA SKORING STANDAR (BBCA, ADRO, PACK, BTC, GOLD)
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
            if not s_idr.empty and len(s_idr) >= 50 and s_idr.iloc[-1] > s_idr.rolling(50).mean().iloc[-1]: score += 25
            if not s_ihsg.empty and len(df) >= 20 and len(s_ihsg) >= 20 and ((df['Close'].iloc[-1] - df['Close'].iloc[-20]) / df['Close'].iloc[-20]) > ((s_ihsg.iloc[-1] - s_ihsg.iloc[-20]) / s_ihsg.iloc[-20]): score += 20

    # ==========================================
    # LOGIKA SKORING TRANSISIONAL (FORU & DOOH)
    # ==========================================
    else:
        score = 0
        
        # Kalkulasi OBV
        obv = np.where(df['Close'] > df['Close'].shift(1), df['Volume'], np.where(df['Close'] < df['Close'].shift(1), -df['Volume'], 0))
        df['OBV'] = pd.Series(obv, index=df.index).cumsum()
        
        # 1. Sector Rotation vs IHSG (20%)
        if not s_ihsg.empty and len(df) >= 20 and len(s_ihsg) >= 20 and ((df['Close'].iloc[-1] - df['Close'].iloc[-20]) / df['Close'].iloc[-20]) > ((s_ihsg.iloc[-1] - s_ihsg.iloc[-20]) / s_ihsg.iloc[-20]): score += 20
        # 2. Medium-Term Trend (15%)
        if cur['Close'] > cur['SMA_50']: score += 15
        # 3. Trend Velocity (15%)
        if cur['MACD'] > cur['Signal']: score += 15
        # 4. RSI Dip Buy (5%)
        if cur['RSI'] < 40 and cur['Close'] > cur['SMA_50']: score += 5
        # 5. Smart Money OBV (20%)
        if not df['OBV'].empty and len(df) >= 20 and df['OBV'].iloc[-1] > df['OBV'].rolling(20).mean().iloc[-1]: score += 20
        
        # 6. Macro Overlay Spesifik (25%)
        if asset_type == "foru":
            if not s_idr.empty and len(s_idr) >= 50 and s_idr.iloc[-1] > s_idr.rolling(50).mean().iloc[-1]: score += 25 # Direct IDR
        elif asset_type == "dooh":
            if not s_tnx.empty and len(s_tnx) >= 50 and s_tnx.iloc[-1] < s_tnx.rolling(50).mean().iloc[-1]: score += 25 # Inverse TNX

    # Evaluasi Threshold 70/30
    if score >= 70: regime = "🟢 Macro Bull Engine"
    elif score <= 30: regime = "🔴 Severe Bear Market"
    else: regime = "⚪ Neutral / Chop"
        
    return price_str, f"{score}%", regime

# --- 2. COMPILE SUMMARY TABLE ---
assets_meta = [
    {"name": "BBCA (Structural Equity)", "ticker": "BBCA.JK", "type": "bbca", "sector": "Financials / Banking"},
    {"name": "ADRO (Cyclical Energy)", "ticker": "ADRO.JK", "type": "adro", "sector": "Energy / Commodities"},
    {"name": "PACK (Commodity / Rights)", "ticker": "PACK.JK", "type": "pack", "sector": "Basic Materials"},
    {"name": "FORU (Mining / HMETD)", "ticker": "FORU.JK", "type": "foru", "sector": "Basic Materials (Transitional)"},
    {"name": "DOOH (Tech/AI Pivot)", "ticker": "DOOH.JK", "type": "dooh", "sector": "Technology (Transitional)"},
    {"name": "Bitcoin (BTC)", "ticker": "BTC-USD", "type": "btc", "sector": "High-Beta Crypto"},
    {"name": "Gold (Safe Haven)", "ticker": "GC=F", "type": "gold", "sector": "Precious Metals"}
]

summary_rows = []
for item in assets_meta:
    price, conviction, regime = calculate_asset_score(item["ticker"], data, item["type"])
    summary_rows.append({
        "Asset Matrix": item["name"],
        "Sector": item["sector"],
        "Current Price": price,
        "Conviction Score": conviction,
        "Regime Status": regime
    })

df_summary = pd.DataFrame(summary_rows)

# --- 3. RENDER UI LAYOUT ---
st.subheader("🌐 Global Macro Pulse & Asset Summary")
st.dataframe(df_summary, use_container_width=True, hide_index=True)
st.divider()

st.subheader("📁 Select Asset Terminal")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown("### 🏦 BBCA")
    st.write("Private structural compounder.")
with col2:
    st.markdown("### ⛏️ ADRO")
    st.write("Cyclical coal exporter.")
with col3:
    st.markdown("### 📦 PACK")
    st.write("Nickel transition & rights issue.")
with col4:
    st.markdown("### 📈 Bitcoin")
    st.write("Global liquidity tracking.")

st.write("")
col5, col6, col7, col8 = st.columns(4)
with col5:
    st.markdown("### 🪙 Gold")
    st.write("Safe-haven & yield opportunity cost.")
with col6:
    st.markdown("### 📰 FORU")
    st.write("Mining pivot & HMETD dynamics.")
with col7:
    st.markdown("### 🏙️ DOOH")
    st.write("AI/Tech pivot accumulation.")
with col8:
    st.empty()

st.markdown("""
<div style='background-color: #1E2127; padding: 20px; border-radius: 10px; border: 1px solid #333; text-align: center; margin-top: 30px;'>
    <p style='color: #AAA; font-size: 14px; margin-bottom: 10px;'>💡 <i>YS Investment Research is provided free as an open quantitative project. If this model helps your portfolio, consider supporting the data feeds:</i></p>
    <a href="https://saweria.co/yourname" target="_blank" style='background-color: #E5A937; color: #000; text-decoration: none; padding: 8px 16px; border-radius: 5px; font-weight: bold; font-size: 14px;'>☕ Support / Donate</a>
</div>
""", unsafe_allow_html=True)
