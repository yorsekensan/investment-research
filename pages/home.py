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

# --- 1. BULK DATA FETCHING (MATCHING MATRIX PAGES WITH period="max") ---
@st.cache_data(ttl=3600)
def fetch_command_center_data():
    tickers = ["BTC-USD", "GC=F", "BBCA.JK", "ADRO.JK", "DX-Y.NYB", "^GSPC", "^TNX", "^JKSE", "IDR=X"]
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

# Helper engine to cleanly process each asset independently
def calculate_asset_score(asset_ticker, data, asset_type):
    # Failsafe 1: Is the ticker completely missing?
    if asset_ticker not in data.columns:
        return "N/A", "🟨🟨🟨🟨🟨🟨 (0B | 6N | 0S)", "⚪ Data Error (Missing Ticker)"
        
    # Failsafe 2: Force data to be numeric, drop NaNs
    s_asset = pd.Series(data[asset_ticker]).apply(pd.to_numeric, errors='coerce').dropna()
    
    # Failsafe 3: Do we have enough trading days to even do the math?
    if s_asset.empty or len(s_asset) < 20:
        return "N/A", "🟨🟨🟨🟨🟨🟨 (0B | 6N | 0S)", "⚪ Data Error (Insufficient Data)"
        
    df = pd.DataFrame({'Close': s_asset})
    
    # Calculate Core Technical Indicators
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
    
    # Failsafe 4: Final check before accessing the last row
    if df.empty:
        return "N/A", "🟨🟨🟨🟨🟨🟨 (0B | 6N | 0S)", "⚪ Data Error (Empty DataFrame)"
        
    cur = df.iloc[-1]
    
    buys = 0
    neutrals = 0
    sells = 0

    # Indicator 1: 200-Day SMA (Structural Trend)
    if pd.notna(cur.get('SMA_200')):
        if cur['Close'] > cur['SMA_200']: buys += 1
        else: sells += 1
    else: neutrals += 1

    # Indicator 2: 50-Day SMA (Medium Trend)
    if pd.notna(cur.get('SMA_50')):
        if cur['Close'] > cur['SMA_50']: buys += 1
        else: sells += 1
    else: neutrals += 1

    # Indicator 3: 14-Day RSI (Valuation / Momentum)
    if pd.notna(cur.get('RSI')):
        if cur['RSI'] < 40: buys += 1
        elif cur['RSI'] > 60: sells += 1
        else: neutrals += 1
    else: neutrals += 1

    # Indicator 4: Fast MACD Cross (Cyclical Momentum)
    if pd.notna(cur.get('MACD')) and pd.notna(cur.get('Signal')):
        if cur['MACD'] > cur['Signal']: buys += 1
        else: sells += 1
    else: neutrals += 1
    
    # Clean macro helpers (Safely coerced to numeric)
    s_dxy = pd.Series(data.get('DX-Y.NYB', pd.Series(dtype=float))).apply(pd.to_numeric, errors='coerce').dropna()
    s_tnx = pd.Series(data.get('^TNX', pd.Series(dtype=float))).apply(pd.to_numeric, errors='coerce').dropna()
    s_ihsg = pd.Series(data.get('^JKSE', pd.Series(dtype=float))).apply(pd.to_numeric, errors='coerce').dropna()
    s_spx = pd.Series(data.get('^GSPC', pd.Series(dtype=float))).apply(pd.to_numeric, errors='coerce').dropna()
    s_idr = pd.Series(data.get('IDR=X', pd.Series(dtype=float))).apply(pd.to_numeric, errors='coerce').dropna()
    
    # Custom 2 macro indicators per asset type
    if asset_type == "btc":
        if not s_dxy.empty and len(s_dxy) >= 50:
            if s_dxy.iloc[-1] < s_dxy.rolling(50).mean().iloc[-1]: buys += 1
            else: sells += 1
        else: neutrals += 1

        if not s_spx.empty and len(df) >= 20 and len(s_spx) >= 20:
            btc_20d = (df['Close'].iloc[-1] - df['Close'].iloc[-20]) / df['Close'].iloc[-20]
            spx_20d = (s_spx.iloc[-1] - s_spx.iloc[-20]) / s_spx.iloc[-20]
            if btc_20d > spx_20d: buys += 1
            else: sells += 1
        else: neutrals += 1

        price_str = f"${cur['Close']:,.2f}"

    elif asset_type == "gold":
        if not s_dxy.empty and len(s_dxy) >= 50:
            if s_dxy.iloc[-1] < s_dxy.rolling(50).mean().iloc[-1]: buys += 1
            else: sells += 1
        else: neutrals += 1

        if not s_tnx.empty and len(s_tnx) >= 50:
            if s_tnx.iloc[-1] < s_tnx.rolling(50).mean().iloc[-1]: buys += 1
            else: sells += 1
        else: neutrals += 1

        price_str = f"${cur['Close']:,.2f}"

    elif asset_type == "bbca":
        if not s_ihsg.empty and len(df) >= 20 and len(s_ihsg) >= 20:
            bbca_20d = (df['Close'].iloc[-1] - df['Close'].iloc[-20]) / df['Close'].iloc[-20]
            ihsg_20d = (s_ihsg.iloc[-1] - s_ihsg.iloc[-20]) / s_ihsg.iloc[-20]
            if bbca_20d > ihsg_20d: buys += 1
            else: sells += 1
        else: neutrals += 1

        if not s_tnx.empty and len(s_tnx) >= 50:
            if s_tnx.iloc[-1] < s_tnx.rolling(50).mean().iloc[-1]: buys += 1
            else: sells += 1
        else: neutrals += 1

        price_str = f"Rp {cur['Close']:,.0f}"

    elif asset_type == "adro":
        if not s_idr.empty and len(s_idr) >= 50:
            if s_idr.iloc[-1] > s_idr.rolling(50).mean().iloc[-1]: buys += 1
            else: sells += 1
        else: neutrals += 1

        if not s_ihsg.empty and len(df) >= 20 and len(s_ihsg) >= 20:
            adro_20d = (df['Close'].iloc[-1] - df['Close'].iloc[-20]) / df['Close'].iloc[-20]
            ihsg_20d = (s_ihsg.iloc[-1] - s_ihsg.iloc[-20]) / s_ihsg.iloc[-20]
            if adro_20d > ihsg_20d: buys += 1
            else: sells += 1
        else: neutrals += 1

        price_str = f"Rp {cur['Close']:,.0f}"
        
    # Generate Visual Distribution Bar
    bar_visual = ("🟩" * buys) + ("🟨" * neutrals) + ("🟥" * sells)
    consensus_str = f"{bar_visual}  ({buys}B | {neutrals}N | {sells}S)"

    # Determine Overall Regime Status
    if buys >= 4:
        regime = "🟢 Macro Buy Zone"
    elif sells >= 4:
        regime = "🔴 Macro Sell Zone"
    else:
        regime = "⚪ Neutral Regime"
        
    return price_str, consensus_str, regime

# --- 2. COMPILE COMMAND CENTER SUMMARY TABLE ---
assets_meta = [
    {"name": "BBCA (Structural Equity)", "ticker": "BBCA.JK", "type": "bbca", "sector": "Financials / Banking"},
    {"name": "ADRO (Cyclical Energy)", "ticker": "ADRO.JK", "type": "adro", "sector": "Energy / Commodities"},
    {"name": "Bitcoin (BTC)", "ticker": "BTC-USD", "type": "btc", "sector": "High-Beta Crypto"},
    {"name": "Gold (Safe Haven)", "ticker": "GC=F", "type": "gold", "sector": "Precious Metals"}
]

summary_rows = []
for item in assets_meta:
    price, consensus, regime = calculate_asset_score(item["ticker"], data, item["type"])
    summary_rows.append({
        "Asset Matrix": item["name"],
        "Sector": item["sector"],
        "Current Price": price,
        "Macro Consensus": consensus,
        "Regime Status": regime
    })

df_summary = pd.DataFrame(summary_rows)

# --- 3. RENDER UI LAYOUT ---
st.subheader("🌐 Global Macro Pulse & Asset Summary")
st.write("Live algorithmic evaluation across all tracked asset classes based on the unified 6-indicator quantitative matrix.")

st.dataframe(
    df_summary, 
    use_container_width=True, 
    hide_index=True
)

st.divider()

st.subheader("📁 Select Asset Terminal")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("### 🏦 BBCA")
    st.write("Private structural compounder & banking leader.")
    
with col2:
    st.markdown("### ⛏️ ADRO")
    st.write("Cyclical coal exporter & currency tailwinds.")
    
with col3:
    st.markdown("### 📈 Bitcoin")
    st.write("Global liquidity & high-beta risk tracking.")
    
with col4:
    st.markdown("### 🪙 Gold")
    st.write("Safe-haven store of value & yield opportunity cost.")

st.write("")

st.markdown("""
<div style='background-color: #1E2127; padding: 20px; border-radius: 10px; border: 1px solid #333; text-align: center;'>
    <p style='color: #AAA; font-size: 14px; margin-bottom: 10px;'>💡 <i>YS Investment Research is provided free as an open quantitative project. If this model helps your portfolio, consider supporting the data feeds:</i></p>
    <a href="https://trakteer.id/yourname" target="_blank" style='background-color: #E5A937; color: #000; text-decoration: none; padding: 8px 16px; border-radius: 5px; font-weight: bold; font-size: 14px;'>☕ Support / Donate</a>
</div>
""", unsafe_allow_html=True)
