import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# ==========================================
# ⚙️ COMMAND CENTER CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="YS Investment Research | Command Center", 
    page_icon="⚡", 
    layout="wide"
)

st.title("⚡ YS Investment Research Terminal")
st.write("Institutional-grade quantitative macro tracking across global equities, digital assets, precious metals, and emerging markets.")
st.divider()

# --- 1. BULK DATA FETCHING ---
@st.cache_data(ttl=3600)
def fetch_command_center_data():
    tickers = ["BTC-USD", "GC=F", "BBCA.JK", "ADRO.JK", "PACK.JK", "DX-Y.NYB", "^GSPC", "^TNX", "^JKSE", "IDR=X"]
    df_raw = yf.download(tickers, period="max", progress=False)
    
    if isinstance(df_raw.columns, pd.MultiIndex):
        if 'Close' in df_raw.columns.levels[0]:
            data = df_raw['Close']
        else:
            data = df_raw.xs('Close', axis=1, level=0, drop_level=True)
    else:
        data = df_raw
        
    return data

try:
    data = fetch_command_center_data()
except Exception as e:
    st.error(f"Failed to fetch live macro data: {e}")
    st.stop()

# Helper engine to cleanly process each asset using the 100-Point Hierarchical Engine
def calculate_asset_score(asset_ticker, data, asset_type):
    # Failsafe 1: Is the ticker missing?
    if asset_ticker not in data.columns:
        return "N/A", "0%", "⚪ Data Error (Missing Ticker)"
        
    # Failsafe 2: Force data to numeric, drop NaNs
    s_asset = pd.Series(data[asset_ticker]).apply(pd.to_numeric, errors='coerce').dropna()
    
    # Failsafe 3: Insufficient data check
    if s_asset.empty or len(s_asset) < 20:
        return "N/A", "0%", "⚪ Data Error (Insufficient Data)"
        
    df = pd.DataFrame({'Close': s_asset})
    
    # Technical Indicators
    df['SMA_50'] = df['Close'].rolling(50).mean()
    df['SMA_200'] = df['Close'].rolling(200).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    
    # Fast MACD (13, 21)
    exp1 = df['Close'].ewm(span=13, adjust=False).mean()
    exp2 = df['Close'].ewm(span=21, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    if df.empty:
        return "N/A", "0%", "⚪ Data Error (Empty DataFrame)"
        
    cur = df.iloc[-1]
    score = 0
    
    # Core Regime Boolean
    is_bull_regime = pd.notna(cur.get('SMA_200')) and cur['Close'] > cur['SMA_200']

    # Indicator 1: 200-Day SMA (Weight: 30%)
    if is_bull_regime:
        score += 30

    # Indicator 2: 50-Day SMA (Weight: 10%)
    if pd.notna(cur.get('SMA_50')) and cur['Close'] > cur['SMA_50']:
        score += 10

    # Indicator 3: Smart RSI (Weight: 5%)
    if pd.notna(cur.get('RSI')):
        if cur['RSI'] < 40 and is_bull_regime:
            score += 5  # Dip buy in a bull regime
            
    # Indicator 4: Fast MACD (Weight: 10%)
    if pd.notna(cur.get('MACD')) and pd.notna(cur.get('Signal')) and cur['MACD'] > cur['Signal']:
        score += 10
    
    # Clean macro series
    s_dxy = pd.Series(data.get('DX-Y.NYB', pd.Series(dtype=float))).apply(pd.to_numeric, errors='coerce').dropna()
    s_tnx = pd.Series(data.get('^TNX', pd.Series(dtype=float))).apply(pd.to_numeric, errors='coerce').dropna()
    s_ihsg = pd.Series(data.get('^JKSE', pd.Series(dtype=float))).apply(pd.to_numeric, errors='coerce').dropna()
    s_spx = pd.Series(data.get('^GSPC', pd.Series(dtype=float))).apply(pd.to_numeric, errors='coerce').dropna()
    s_idr = pd.Series(data.get('IDR=X', pd.Series(dtype=float))).apply(pd.to_numeric, errors='coerce').dropna()
    
    # Custom Macro Evaluation (25% for Factor 1, 20% for Factor 2)
    if asset_type == "btc":
        if not s_dxy.empty and len(s_dxy) >= 50 and s_dxy.iloc[-1] < s_dxy.rolling(50).mean().iloc[-1]:
            score += 25
        if not s_spx.empty and len(df) >= 20 and len(s_spx) >= 20:
            btc_20d = (df['Close'].iloc[-1] - df['Close'].iloc[-20]) / df['Close'].iloc[-20]
            spx_20d = (s_spx.iloc[-1] - s_spx.iloc[-20]) / s_spx.iloc[-20]
            if btc_20d > spx_20d: score += 20
        price_str = f"${cur['Close']:,.2f}"

    elif asset_type == "gold":
        if not s_dxy.empty and len(s_dxy) >= 50 and s_dxy.iloc[-1] < s_dxy.rolling(50).mean().iloc[-1]:
            score += 25
        if not s_tnx.empty and len(s_tnx) >= 50 and s_tnx.iloc[-1] < s_tnx.rolling(50).mean().iloc[-1]:
            score += 20
        price_str = f"${cur['Close']:,.2f}"

    elif asset_type == "bbca":
        if not s_tnx.empty and len(s_tnx) >= 50 and s_tnx.iloc[-1] < s_tnx.rolling(50).mean().iloc[-1]:
            score += 25
        if not s_ihsg.empty and len(df) >= 20 and len(s_ihsg) >= 20:
            bbca_20d = (df['Close'].iloc[-1] - df['Close'].iloc[-20]) / df['Close'].iloc[-20]
            ihsg_20d = (s_ihsg.iloc[-1] - s_ihsg.iloc[-20]) / s_ihsg.iloc[-20]
            if bbca_20d > ihsg_20d: score += 20
        price_str = f"Rp {cur['Close']:,.0f}"

    elif asset_type == "adro":
        if not s_idr.empty and len(s_idr) >= 50 and s_idr.iloc[-1] > s_idr.rolling(50).mean().iloc[-1]:
            score += 25
        if not s_ihsg.empty and len(df) >= 20 and len(s_ihsg) >= 20:
            adro_20d = (df['Close'].iloc[-1] - df['Close'].iloc[-20]) / df['Close'].iloc[-20]
            ihsg_20d = (s_ihsg.iloc[-1] - s_ihsg.iloc[-20]) / s_ihsg.iloc[-20]
            if adro_20d > ihsg_20d: score += 20
        price_str = f"Rp {cur['Close']:,.0f}"
        
    elif asset_type == "pack":
        # FLIPPED to Direct (>): Weak IDR boosts USD-denominated nickel revenue
        if not s_idr.empty and len(s_idr) >= 50 and s_idr.iloc[-1] > s_idr.rolling(50).mean().iloc[-1]:
            score += 25
        if not s_ihsg.empty and len(df) >= 20 and len(s_ihsg) >= 20:
            pack_20d = (df['Close'].iloc[-1] - df['Close'].iloc[-20]) / df['Close'].iloc[-20]
            ihsg_20d = (s_ihsg.iloc[-1] - s_ihsg.iloc[-20]) / s_ihsg.iloc[-20]
            if pack_20d > ihsg_20d: score += 20
        price_str = f"Rp {cur['Close']:,.0f}"
        
    # --- UNIFIED 70/30 REGIME THRESHOLD --- 21/08/2026
    if score >= 70:
        regime = "🟢 Macro Bull Engine"
    elif score <= 30:
        regime = "🔴 Severe Bear Market"
    else:
        regime = "⚪ Neutral / Chop"
        
    return price_str, f"{score}%", regime

# --- 2. COMPILE SUMMARY TABLE ---
assets_meta = [
    {"name": "BBCA (Structural Equity)", "ticker": "BBCA.JK", "type": "bbca", "sector": "Financials / Banking"},
    {"name": "ADRO (Cyclical Energy)", "ticker": "ADRO.JK", "type": "adro", "sector": "Energy / Commodities"},
    {"name": "PACK (Small Cap)", "ticker": "PACK.JK", "type": "pack", "sector": "Manufacturing / Packaging"},
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
st.write("Live algorithmic evaluation across all tracked asset classes based on the unified 100-Point Hierarchical Conviction Matrix.")

st.dataframe(
    df_summary, 
    use_container_width=True, 
    hide_index=True
)

st.divider()

st.subheader("📁 Select Asset Terminal")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown("### 🏦 BBCA")
    st.write("Private structural compounder & banking leader.")
    
with col2:
    st.markdown("### ⛏️ ADRO")
    st.write("Cyclical coal exporter & currency tailwinds.")

with col3:
    st.markdown("### 📦 PACK")
    st.write("Small-cap packaging & rights issue catalyst.")
    
with col4:
    st.markdown("### 📈 Bitcoin")
    st.write("Global liquidity & high-beta risk tracking.")
    
with col5:
    st.markdown("### 🪙 Gold")
    st.write("Safe-haven store of value & yield opportunity cost.")

st.write("")

st.markdown("""
<div style='background-color: #1E2127; padding: 20px; border-radius: 10px; border: 1px solid #333; text-align: center;'>
    <p style='color: #AAA; font-size: 14px; margin-bottom: 10px;'>💡 <i>YS Investment Research is provided free as an open quantitative project. If this model helps your portfolio, consider supporting the data feeds:</i></p>
    <a href="https://saweria.co/yorsekensan" target="_blank" style='background-color: #E5A937; color: #000; text-decoration: none; padding: 8px 16px; border-radius: 5px; font-weight: bold; font-size: 14px;'>☕ Support / Donate</a>
</div>
""", unsafe_allow_html=True)
