import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from disclaimer import render_disclaimer

PAGE_TITLE = "FORU (Media & Corp Action)"
PAGE_ICON = "📰"
TICKER = "FORU.JK"
DESCRIPTION = "Live quantitative tracking of domestic advertising dynamics and structural corporate action pricing (Rights Issue/OWK impacts)."

st.set_page_config(page_title=f"{PAGE_TITLE} Matrix", page_icon=PAGE_ICON, layout="wide")
st.title(f"{PAGE_ICON} {PAGE_TITLE} Macro Matrix")
st.write(DESCRIPTION)
render_disclaimer()
st.divider()

@st.cache_data(ttl=3600)
def fetch_custom_data():
    df_asset = yf.download(TICKER, period="max", progress=False)
    if isinstance(df_asset.columns, pd.MultiIndex): df_asset.columns = df_asset.columns.droplevel(1)
    df_ihsg = yf.download("^JKSE", period="max", progress=False)
    if isinstance(df_ihsg.columns, pd.MultiIndex): df_ihsg.columns = df_ihsg.columns.droplevel(1)
    df_idr = yf.download("IDR=X", period="max", progress=False)
    if isinstance(df_idr.columns, pd.MultiIndex): df_idr.columns = df_idr.columns.droplevel(1)

    df_asset['SMA_50'] = df_asset['Close'].rolling(window=50).mean()
    df_asset['SMA_200'] = df_asset['Close'].rolling(window=200).mean()
    delta = df_asset['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df_asset['RSI'] = 100 - (100 / (1 + (gain / loss)))
    df_asset['MACD'] = df_asset['Close'].ewm(span=13, adjust=False).mean() - df_asset['Close'].ewm(span=21, adjust=False).mean()
    df_asset['Signal_Line'] = df_asset['MACD'].ewm(span=9, adjust=False).mean()
    df_asset['MACD_Hist'] = df_asset['MACD'] - df_asset['Signal_Line']
    
    df_idr['SMA_50'] = df_idr['Close'].rolling(window=50).mean()
    asset_20d = (df_asset['Close'].iloc[-1] - df_asset['Close'].iloc[-20]) / df_asset['Close'].iloc[-20] * 100
    ihsg_20d = (df_ihsg['Close'].iloc[-1] - df_ihsg['Close'].iloc[-20]) / df_ihsg['Close'].iloc[-20] * 100

    return df_asset.dropna(), df_idr.dropna(), asset_20d, ihsg_20d

try:
    df, df_idr, asset_20d, ihsg_20d = fetch_custom_data()
except Exception as e:
    st.error("Failed to fetch live macro data. Yahoo Finance might be rate-limiting.")
    st.stop()

current_price, current_rsi, current_macd, current_signal = float(df['Close'].iloc[-1]), float(df['RSI'].iloc[-1]), float(df['MACD'].iloc[-1]), float(df['Signal_Line'].iloc[-1])
current_idr, idr_sma50 = float(df_idr['Close'].iloc[-1]), float(df_idr['SMA_50'].iloc[-1])

conviction_score = 0
indicators = []

def add_ind(metric, weight, value, signal, explanation):
    indicators.append({"Metric": metric, "Weight": weight, "Current Value": value, "Signal": signal, "How to Read": explanation})

is_bull_regime = pd.notna(df['SMA_200'].iloc[-1]) and (current_price > df['SMA_200'].iloc[-1])

if pd.notna(df['SMA_200'].iloc[-1]):
    if current_price > df['SMA_200'].iloc[-1]:
        conviction_score += 30; add_ind("Long-Term Trend", "30%", "Price > 200 SMA", "🟢 Buy", "Structural bull trend confirmed despite corporate action noise.")
    else:
        add_ind("Long-Term Trend", "30%", "Price < 200 SMA", "🔴 Sell", "Structural contraction or severe dilutive pricing impact.")

if pd.notna(current_idr) and pd.notna(idr_sma50):
    if current_idr < idr_sma50:
        conviction_score += 25; add_ind("Currency Tailwind (Inverse IDR)", "25%", f"Rp {current_idr:,.0f}", "🟢 Buy", "Strong Rupiah limits inflation, boosting corporate marketing/ad budgets.")
    else:
        add_ind("Currency Tailwind (Inverse IDR)", "25%", f"Rp {current_idr:,.0f}", "🔴 Sell", "Weak Rupiah cuts into client margins, reducing domestic ad spend.")

if pd.notna(asset_20d) and pd.notna(ihsg_20d):
    if asset_20d > ihsg_20d:
        conviction_score += 20; add_ind("Sector Rotation (vs IHSG 20d)", "20%", "FORU > IHSG", "🟢 Buy", "Institutional capital is accumulating despite / because of corporate action mechanics.")
    else:
        add_ind("Sector Rotation (vs IHSG 20d)", "20%", "FORU < IHSG", "🔴 Sell", "Underperforming the index indicates lack of market interest.")

if pd.notna(df['SMA_50'].iloc[-1]):
    if current_price > df['SMA_50'].iloc[-1]:
        conviction_score += 10; add_ind("Medium-Term Trend (50 SMA)", "10%", "Price > 50 SMA", "🟢 Buy", "Quarterly momentum remains robust.")
    else:
        add_ind("Medium-Term Trend (50 SMA)", "10%", "Price < 50 SMA", "🔴 Sell", "Quarterly deceleration.")

if pd.notna(current_macd) and pd.notna(current_signal):
    if current_macd > current_signal:
        conviction_score += 10; add_ind("Trend Velocity (MACD)", "10%", "MACD > Signal", "🟢 Buy", "Short-term bullish acceleration.")
    else:
        add_ind("Trend Velocity (MACD)", "10%", "MACD < Signal", "🔴 Sell", "Downside momentum.")

if pd.notna(current_rsi):
    if current_rsi < 40:
        if is_bull_regime: conviction_score += 5; add_ind("RSI", "5%", f"RSI {current_rsi:.1f}", "🟢 Buy", "Oversold in macro bull regime. Potential discount.")
        else: add_ind("RSI", "5%", f"RSI {current_rsi:.1f}", "🔴 Sell", "Oversold in bear regime. Falling knife.")
    elif current_rsi > 60: add_ind("RSI", "5%", f"RSI {current_rsi:.1f}", "🔴 Sell", "Overbought and prone to sharp correction.")
    else: add_ind("RSI", "5%", f"RSI {current_rsi:.1f}", "⚪ Neutral", "Balanced.")

col1, col2 = st.columns([2.5, 1])
timeframe_selector = dict(buttons=list([dict(count=3, label="3M", step="month", stepmode="backward"), dict(count=6, label="6M", step="month", stepmode="backward"), dict(count=1, label="1Y", step="year", stepmode="backward"), dict(step="all", label="All")]), bgcolor="#1E2127", activecolor="#E5A937", font=dict(color="#FFFFFF", size=11), x=0.0, y=1.15)

with col1:
    fig_price = go.Figure()
    fig_price.add_trace(go.Scatter(x=df.index, y=df['Close'], name='Price', line=dict(color='#2ECC71', width=2)))
    fig_price.add_trace(go.Scatter(x=df.index, y=df['SMA_200'], name='200 SMA', line=dict(color='white', width=1, dash='dash')))
    fig_price.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], name='50 SMA', line=dict(color='#E5A937', width=1)))
    fig_price.update_xaxes(rangeselector=timeframe_selector, type="date")
    fig_price.update_layout(template="plotly_dark", height=420, margin=dict(l=0, r=0, t=50, b=0), plot_bgcolor='#0E1117', paper_bgcolor='#0E1117')
    st.plotly_chart(fig_price, use_container_width=True)

with col2:
    st.subheader("Live Metrics")
    st.metric("FORU Price", f"Rp {current_price:,.0f}")
    st.metric("USD/IDR Exchange", f"Rp {current_idr:,.0f}")
    st.metric("20D Rel. Leadership", f"{asset_20d:.1f}%", delta=f"{asset_20d - ihsg_20d:.1f}% vs IHSG", delta_color="normal" if asset_20d > ihsg_20d else "inverse")

st.divider()
st.subheader(f"Algorithmic Conviction Score: {conviction_score}%")
st.progress(conviction_score / 100.0)

if conviction_score >= 70: st.success(f"🟢 **MACRO BULL ENGINE:** Domestic tailwinds and price action support an uptrend.")
elif conviction_score <= 30: st.error(f"🔴 **SEVERE BEAR MARKET:** Fundamentals and technicals broke down. High dilution/distribution risk.")
else: st.info(f"⚪ **NEUTRAL / SIDEWAYS CHOP:** Mixed signals. Await structural breakout.")

with st.expander("📊 View Detailed Indicator Weights", expanded=True): st.table(pd.DataFrame(indicators))

st.markdown("""
<div style='background-color: #1E2127; padding: 20px; border-radius: 10px; border: 1px solid #333; text-align: center; margin-top: 30px;'>
    <p style='color: #AAA; font-size: 14px; margin-bottom: 10px;'>💡 <i>YS Investment Research is provided free as an open quantitative project. If this model helps your portfolio, consider supporting the data feeds:</i></p>
    <a href="https://saweria.co/yourname" target="_blank" style='background-color: #E5A937; color: #000; text-decoration: none; padding: 8px 16px; border-radius: 5px; font-weight: bold; font-size: 14px;'>☕ Support / Donate</a>
</div>
""", unsafe_allow_html=True)
