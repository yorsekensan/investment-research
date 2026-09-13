import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from disclaimer import render_disclaimer

PAGE_TITLE = "DOOH (Tech/AI Pivot)"
PAGE_ICON = "🏙️"
TICKER = "DOOH.JK"

st.set_page_config(page_title=f"{PAGE_TITLE} Matrix", page_icon=PAGE_ICON, layout="wide")
st.title(f"{PAGE_ICON} {PAGE_TITLE} Macro Matrix")
st.write("Quantitative tracking for AI/Tech pivot. Optimized for Smart Money accumulation (OBV) and sensitivity to global interest rates (^TNX).")
render_disclaimer()
st.divider()

@st.cache_data(ttl=3600)
def fetch_custom_data():
    df = yf.download(TICKER, period="max", progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
    df_ihsg = yf.download("^JKSE", period="max", progress=False)
    if isinstance(df_ihsg.columns, pd.MultiIndex): df_ihsg.columns = df_ihsg.columns.droplevel(1)
    
    # 💥 Menggunakan US 10-Year Yield untuk valuasi aset Tech/AI
    df_tnx = yf.download("^TNX", period="max", progress=False)
    if isinstance(df_tnx.columns, pd.MultiIndex): df_tnx.columns = df_tnx.columns.droplevel(1)

    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    
    # OBV
    obv = np.where(df['Close'] > df['Close'].shift(1), df['Volume'], 
          np.where(df['Close'] < df['Close'].shift(1), -df['Volume'], 0))
    df['OBV'] = pd.Series(obv, index=df.index).cumsum()
    df['OBV_SMA_20'] = df['OBV'].rolling(window=20).mean()

    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    df['MACD'] = df['Close'].ewm(span=13, adjust=False).mean() - df['Close'].ewm(span=21, adjust=False).mean()
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    df_tnx['SMA_50'] = df_tnx['Close'].rolling(window=50).mean()
    asset_20d = (df['Close'].iloc[-1] - df['Close'].iloc[-20]) / df['Close'].iloc[-20] * 100
    ihsg_20d = (df_ihsg['Close'].iloc[-1] - df_ihsg['Close'].iloc[-20]) / df_ihsg['Close'].iloc[-20] * 100

    return df.dropna(), df_tnx.dropna(), asset_20d, ihsg_20d

try:
    df, df_macro, asset_20d, ihsg_20d = fetch_custom_data()
except Exception:
    st.error("Failed to fetch live data.")
    st.stop()

current_price = float(df['Close'].iloc[-1])
conviction_score = 0
indicators = []
def add_ind(metric, weight, value, signal, exp): indicators.append({"Metric": metric, "Weight": weight, "Current Value": value, "Signal": signal, "How to Read": exp})

# 1. Macro Overlay: US 10Y Yields Inverse (Future Tech/Data Center Valuation) - 25%
macro_cur = float(df_macro['Close'].iloc[-1])
macro_sma = float(df_macro['SMA_50'].iloc[-1])
if macro_cur < macro_sma:
    conviction_score += 25; add_ind("Macro: ^TNX (Inverse)", "25%", f"{macro_cur:.2f}%", "🟢 Buy", "Falling global yields drive liquidity into speculative Tech/AI growth assets.")
else:
    add_ind("Macro: ^TNX (Inverse)", "25%", f"{macro_cur:.2f}%", "🔴 Sell", "High interest rates crush growth and data center valuations.")

# 2. Smart Money (OBV) - 20%
if float(df['OBV'].iloc[-1]) > float(df['OBV_SMA_20'].iloc[-1]):
    conviction_score += 20; add_ind("Smart Money (OBV)", "20%", "OBV > MA20", "🟢 Buy", "Institutional volume accumulating before rumor confirmation.")
else:
    add_ind("Smart Money (OBV)", "20%", "OBV < MA20", "🔴 Sell", "Weak volume support.")

# 3. Sector Rotation - 20%
if asset_20d > ihsg_20d: conviction_score += 20; add_ind("Sector Rotation", "20%", "DOOH > IHSG", "🟢 Buy", "Outperforming index.")
else: add_ind("Sector Rotation", "20%", "DOOH < IHSG", "🔴 Sell", "Underperforming index.")

# 4. Trend (50 SMA) - 15%
if current_price > df['SMA_50'].iloc[-1]: conviction_score += 15; add_ind("Trend (50 SMA)", "15%", "Price > 50 SMA", "🟢 Buy", "Uptrend structural.")
else: add_ind("Trend (50 SMA)", "15%", "Price < 50 SMA", "🔴 Sell", "Downtrend.")

# 5. Velocity (MACD) - 15%
if df['MACD'].iloc[-1] > df['Signal_Line'].iloc[-1]: conviction_score += 15; add_ind("Velocity (MACD)", "15%", "MACD > Signal", "🟢 Buy", "Accelerating.")
else: add_ind("Velocity (MACD)", "15%", "MACD < Signal", "🔴 Sell", "Decelerating.")

# 6. RSI - 5%
rsi = float(df['RSI'].iloc[-1])
if rsi < 40 and current_price > df['SMA_50'].iloc[-1]: conviction_score += 5; add_ind("RSI", "5%", f"{rsi:.1f}", "🟢 Buy", "Oversold.")
elif rsi > 65: add_ind("RSI", "5%", f"{rsi:.1f}", "🔴 Sell", "Overbought.")
else: add_ind("RSI", "5%", f"{rsi:.1f}", "⚪ Neutral", "Balanced.")

col1, col2 = st.columns([2.5, 1])
with col1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name='DOOH Price', line=dict(color='#3498DB', width=2)))
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], name='50 SMA', line=dict(color='#E5A937', width=1)))
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0, r=0, t=30, b=0), plot_bgcolor='#0E1117', paper_bgcolor='#0E1117')
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Corporate Action Anchor")
    corp_price = st.number_input("Target / Corp Action Price (Rp)", value=250, step=10)
    st.metric("DOOH Live Price", f"Rp {current_price:,.0f}")
    diff = ((current_price - corp_price) / corp_price) * 100
    st.metric("Premium / Discount", f"{diff:.1f}%", delta=f"{current_price - corp_price:,.0f} Rp", delta_color="inverse")
    
st.divider()
st.subheader(f"Transitional Engine Score: {conviction_score}%")
st.progress(conviction_score / 100.0)

if conviction_score >= 70: st.success(f"🟢 **ACCUMULATION PHASE:** Tech pivot narratives are supported by volume and macro liquidity.")
elif conviction_score <= 30: st.error(f"🔴 **DISTRIBUTION PHASE:** Lack of volume and unfavorable macro conditions.")
else: st.info(f"⚪ **CHOPPY / NOISE:** Await clearer breakout.")

with st.expander("📊 View Detailed Engine Breakdown", expanded=True): st.table(pd.DataFrame(indicators))

st.markdown("""<div style='background-color: #1E2127; padding: 20px; text-align: center; margin-top: 30px;'><a href="https://saweria.co/yourname" target="_blank" style='background-color: #E5A937; color: #000; text-decoration: none; padding: 8px 16px; border-radius: 5px; font-weight: bold;'>☕ Support / Donate</a></div>""", unsafe_allow_html=True)
