import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Market Dashboard", layout="wide")

st.title("Market Intelligence Dashboard")
st.caption("Quantitative regime monitoring.")

# --- LIVE PRICE FETCHING ENGINE ---
@st.cache_data(ttl=60)
def get_live_price(ticker):
    try:
        df = yf.download(ticker, period="1d", interval="1m", progress=False)
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                return float(df['Close'].iloc[-1].values[0])
            return float(df['Close'].iloc[-1])
    except Exception:
        pass
    return None

btc_price = get_live_price("BTC-USD")
bbca_price = get_live_price("BBCA.JK")
adro_price = get_live_price("ADRO.JK")
gold_price = get_live_price("GC=F") # Added Gold Pricing

# ==========================================
# 🟢 CRYPTO ECOSYSTEM SECTION
# ==========================================
st.divider()

col1, col2, col3 = st.columns([1, 8, 3])
with col1:
    st.image("https://cryptologos.cc/logos/bitcoin-btc-logo.png", width=40)
with col2:
    st.subheader("Crypto Assets")
with col3:
    if btc_price:
        st.metric(label="Live BTC/USD", value=f"${btc_price:,.2f}")
    else:
        st.metric(label="Live BTC/USD", value="Data Offline")

st.page_link("pages/btc_macro.py", label="Bitcoin (BTC) Macro Regime", icon="📈")

# ==========================================
# 🟡 COMMODITIES SECTION
# ==========================================
st.divider()

col7, col8, col9 = st.columns([1, 8, 3])
with col7:
    # General gold/commodity icon
    st.image("https://cdn-icons-png.flaticon.com/512/3665/3665961.png", width=40)
with col8:
    st.subheader("Commodities")
with col9:
    if gold_price:
        st.metric(label="Gold (GC=F)", value=f"${gold_price:,.2f}")
    else:
        st.metric(label="Gold (GC=F)", value="Data Offline")

st.page_link("pages/gold_macro.py", label="Gold (GC=F) Macro Matrix", icon="🪙")

# ==========================================
# 🔵 IDX EQUITIES SECTION
# ==========================================
st.divider()

col4, col5, col6 = st.columns([1, 8, 3])
with col4:
    st.image("https://cdn-icons-png.flaticon.com/512/2422/2422323.png", width=40)
with col5:
    st.subheader("IDX Equities")
with col6:
    if bbca_price:
        st.metric(label="BBCA", value=f"Rp{bbca_price:,.0f}")
    else:
        st.metric(label="BBCA", value="Data Offline")
        
    if adro_price:
        st.metric(label="ADRO", value=f"Rp{adro_price:,.0f}")
    else:
        st.metric(label="ADRO", value="Data Offline")

st.page_link("pages/bbca_matrix.py", label="Bank Central Asia (BBCA.JK) Equity Matrix", icon="🏦")
st.page_link("pages/adro_matrix.py", label="Adaro Energy (ADRO.JK) Cyclical Matrix", icon="⛏️")
