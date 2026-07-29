import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="YS Research | Command Center", layout="wide")

# --- HERO SECTION (VALUE PROPOSITION) ---
st.markdown("<h1 style='text-align: center;'>YS Investment Research</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align: center; color: #888888;'>Emotionless, Algorithmic Clarity in Chaotic Markets.</h4>", unsafe_allow_html=True)
st.write("") # spacing
st.info("**Welcome.** Our quantitative engine monitors global liquidity, momentum, and volume flow to dictate macro asset allocation. Do not guess the market regime. Let the math dictate the exposure.")
st.divider()

# --- LIVE MARKET TICKER ---
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
gold_price = get_live_price("GC=F")
bbca_price = get_live_price("BBCA.JK")

st.subheader("📡 Live Market Monitor")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="Bitcoin (BTC/USD)", value=f"${btc_price:,.2f}" if btc_price else "Offline")
with col2:
    st.metric(label="Gold (GC=F)", value=f"${gold_price:,.2f}" if gold_price else "Offline")
with col3:
    st.metric(label="Bank Central Asia (BBCA)", value=f"Rp{bbca_price:,.0f}" if bbca_price else "Offline")

# --- ALGORITHMIC VERDICT (GATED) ---
st.divider()
st.subheader("🤖 Algorithmic Verdict")
st.write("Our quantitative engine has evaluated all active macro indicators for this asset.")

# Toggle this to True to see what paid users see, False for free users
is_premium = False 

if is_premium:
    # 🟢 WHAT PAID USERS SEE: The Unlocked Signal 
    if buy_count >= 4:
        st.success(f"🟢 **MACRO BUY ZONE** — Indicator Consensus: {buy_count} Buy Signals Aligned")
    elif sell_count >= 4:
        st.error(f"🔴 **MACRO SELL ZONE** — Indicator Consensus: {sell_count} Sell Signals Aligned")
    else:
        st.info(f"⚪ **NEUTRAL REGIME** — Consensus Mixed ({buy_count} Buy / {sell_count} Sell). Wait for alignment.")
else:
    # 🔒 WHAT FREE USERS SEE: The Paywall Box
    st.markdown("""
    <div style='background-color: #1E2127; padding: 30px; border-radius: 10px; border: 1px solid #444; text-align: center;'>
        <h2 style='color: #888; margin-bottom: 5px;'>🔒 PREMIUM MACRO SIGNAL</h2>
        <p style='color: #AAA; font-size: 16px;'>Indicator Consensus: <b>[ LOCKED ]</b></p>
        <p style='color: #AAA; font-size: 16px; margin-bottom: 20px;'>Current Regime: <b>[ LOCKED ]</b></p>
        <a href="#" style='background-color: #E5A937; color: #000; text-decoration: none; padding: 12px 24px; border-radius: 5px; font-weight: bold; font-size: 16px;'>Upgrade to Unlock Signal ➔</a>
    </div>
    """, unsafe_allow_html=True)

# --- CALL TO ACTION (THE FUNNEL) ---
st.subheader("⚖️ Start Here: Design Your Portfolio")
st.write("Before diving into individual asset matrices, determine your baseline macro allocation. Use our proprietary algorithmic allocator to generate your custom risk-adjusted portfolio.")

if st.button("Launch Portfolio Allocator ➔", use_container_width=True, type="primary"):
    st.switch_page("pages/portofolio_allocator.py")

st.write("")

# --- ASSET DISCOVERY ---
st.subheader("🔍 Explore Quantitative Matrices")
col4, col5 = st.columns(2)

with col4:
    st.markdown("### Public Matrices")
    st.write("Test our underlying logic on structural blue-chip equities.")
    if st.button("View BBCA Matrix (Free)"):
         st.switch_page("pages/bbca_matrix.py")

with col5:
    st.markdown("### Premium Matrices")
    st.write("Unlock high-beta crypto and safe-haven macro indicators.")
    st.page_link("pages/btc_macro.py", label="View Bitcoin", icon="🔒")
    st.page_link("pages/gold_macro.py", label="View Gold", icon="🔒")
    st.page_link("pages/adro_matrix.py", label="View ADRO", icon="🔒")
