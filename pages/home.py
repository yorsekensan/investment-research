import streamlit as st
import yfinance as yf
import pandas as pd

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

# --- 1. BULK DATA FETCHING & CALENDAR CLEANING ---
@st.cache_data(ttl=3600)
def fetch_command_center_data():
    tickers = ["BTC-USD", "GC=F", "BBCA.JK", "ADRO.JK", "DX-Y.NYB", "^GSPC", "^TNX", "^JKSE", "IDR=X"]
    # Fetch 2y period to guarantee 200+ trading days for SMA_200
    df_raw = yf.download(tickers, period="2y", progress=False)
    
    # Cleanly extract Close prices regardless of yfinance MultiIndex version
    if isinstance(df_raw.columns, pd.MultiIndex):
        if 'Close' in df_raw.columns.levels[0]:
            data = df_raw['Close']
        else:
            data = df_raw.xs('Close', axis=1, level=0, drop_level=True)
    else:
        data = df_raw
        
    # Forward-fill and back-fill missing calendar/timezone gaps
    data = data.ffill().bfill()
    return data

try:
    data = fetch_command_center_data()
except Exception as e:
    st.error(f"Failed to fetch live macro data: {e}")
    st.stop()

# Helper engine to calculate 6-indicator score consistently
def calculate_asset_score(asset_ticker, data, asset_type):
    if asset_ticker not in data.columns:
        return "N/A", "0 / 6 Buy", "⚪ Data Error"
        
    df = pd.DataFrame(data[asset_ticker].dropna())
    df.columns = ['Close']
    
    # Calculate indicators
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
    
    # Safe extraction of latest valid row
    df_clean = df.dropna()
    if df_clean.empty:
        cur = df.iloc[-1]
    else:
        cur = df_clean.iloc[-1]
    
    # Base 4 technical indicators
    buys = 0
    if pd.notna(cur.get('SMA_200')) and cur['Close'] > cur['SMA_200']: buys += 1
    if pd.notna(cur.get('SMA_50')) and cur['Close'] > cur['SMA_50']: buys += 1
    if pd.notna(cur.get('RSI')) and cur['RSI'] < 40: buys += 1
    if pd.notna(cur.get('MACD')) and pd.notna(cur.get('Signal')) and cur['MACD'] > cur['Signal']: buys += 1
    
    # Custom 2 macro indicators depending on asset type
    if asset_type == "btc":
        dxy_sma50 = data['DX-Y.NYB'].rolling(50).mean().iloc[-1]
        if data['DX-Y.NYB'].iloc[-1] < dxy_sma50: buys += 1
        btc_20d = (data['BTC-USD'].iloc[-1] - data['BTC-USD'].iloc[-20]) / data['BTC-USD'].iloc[-20]
        spx_20d = (data['^GSPC'].iloc[-1] - data['^GSPC'].iloc[-20]) / data['^GSPC'].iloc[-20]
        if btc_20d > spx_20d: buys += 1
        price_str = f"${cur['Close']:,.2f}"

    elif asset_type == "gold":
        dxy_sma50 = data['DX-Y.NYB'].rolling(50).mean().iloc[-1]
        tnx_sma50 = data['^TNX'].rolling(50).mean().iloc[-1]
        if data['DX-Y.NYB'].iloc[-1] < dxy_sma50: buys += 1
        if data['^TNX'].iloc[-1] < tnx_sma50: buys += 1
        price_str = f"${cur['Close']:,.2f}"

    elif asset_type == "bbca":
        bbca_20d = (data['BBCA.JK'].iloc[-1] - data['BBCA.JK'].iloc[-20]) / data['BBCA.JK'].iloc[-20]
        ihsg_20d = (data['^JKSE'].iloc[-1] - data['^JKSE'].iloc[-20]) / data['^JKSE'].iloc[-20]
        tnx_sma50 = data['^TNX'].rolling(50).mean().iloc[-1]
        if bbca_20d > ihsg_20d: buys += 1
        if data['^TNX'].iloc[-1] < tnx_sma50: buys += 1
        price_str = f"Rp {cur['Close']:,.0f}"

    elif asset_type == "adro":
        idr_sma50 = data['IDR=X'].rolling(50).mean().iloc[-1]
        if data['IDR=X'].iloc[-1] > idr_sma50: buys += 1
        adro_20d = (data['ADRO.JK'].iloc[-1] - data['ADRO.JK'].iloc[-20]) / data['ADRO.JK'].iloc[-20]
        ihsg_20d = (data['^JKSE'].iloc[-1] - data['^JKSE'].iloc[-20]) / data['^JKSE'].iloc[-20]
        if adro_20d > ihsg_20d: buys += 1
        price_str = f"Rp {cur['Close']:,.0f}"
        
    # Determine Regime Status
    if buys >= 4:
        regime = "🟢 Macro Buy Zone"
    elif buys <= 2:
        regime = "🔴 Macro Sell Zone"
    else:
        regime = "⚪ Neutral Regime"
        
    return price_str, f"{buys} / 6 Buy", regime

# --- 2. COMPILE COMMAND CENTER SUMMARY TABLE ---
assets_meta = [
    {"name": "BBCA (Structural Equity)", "ticker": "BBCA.JK", "type": "bbca", "sector": "Financials / Banking"},
    {"name": "ADRO (Cyclical Energy)", "ticker": "ADRO.JK", "type": "adro", "sector": "Energy / Commodities"},
    {"name": "Bitcoin (BTC)", "ticker": "BTC-USD", "type": "btc", "sector": "High-Beta Crypto"},
    {"name": "Gold (Safe Haven)", "ticker": "GC=F", "type": "gold", "sector": "Precious Metals"}
]

summary_rows = []
for item in assets_meta:
    price, score, regime = calculate_asset_score(item["ticker"], data, item["type"])
    summary_rows.append({
        "Asset Matrix": item["name"],
        "Sector": item["sector"],
        "Current Price": price,
        "Macro Consensus": score,
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
