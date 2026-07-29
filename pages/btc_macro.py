import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="BTC Matrix", layout="wide")

st.title("📊 Bitcoin (BTC) Macro Regime")
st.caption("Quantitative tracking using custom Fibonacci MACD and Volume Flow.")

# --- 1. SAFE DATA FETCHING ---
@st.cache_data(ttl=300)
def fetch_btc_data():
    try:
        df = yf.download("BTC-USD", period="max", progress=False)
        if not df.empty and isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        return df
    except Exception:
        return pd.DataFrame()

df = fetch_btc_data()

if df.empty or len(df) < 200:
    st.warning("⚠️ Market data provider (yfinance) is temporarily busy. Please refresh.")
    st.stop()

# --- 2. CALCULATE INDICATORS ---
# Trend & 200 DMA
df["MA50"] = df["Close"].rolling(50).mean()
df["MA200"] = df["Close"].rolling(200).mean()
df["pct_vs_200ma"] = (df["Close"] / df["MA200"] - 1) * 100

# RSI
delta = df["Close"].diff()
gain = delta.clip(lower=0).rolling(14).mean()
loss = (-delta.clip(upper=0)).rolling(14).mean()
rs = gain / loss
df["RSI14"] = 100 - (100 / (1 + rs))

# Bollinger Bands
ma20 = df["Close"].rolling(20).mean()
std20 = df["Close"].rolling(20).std()
df["Upper_BB"] = ma20 + (2 * std20)
df["Lower_BB"] = ma20 - (2 * std20)
df["BB_pctB"] = (df["Close"] - df["Lower_BB"]) / (df["Upper_BB"] - df["Lower_BB"])

# Custom Fibonacci MACD (13, 21)
df["EMA13"] = df["Close"].ewm(span=13, adjust=False).mean()
df["EMA21"] = df["Close"].ewm(span=21, adjust=False).mean()
df["MACD"] = df["EMA13"] - df["EMA21"]
df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

# On-Balance Volume (OBV)
df['Direction'] = np.sign(df['Close'].diff())
df['OBV'] = (df['Direction'] * df['Volume']).fillna(0).cumsum()
df['OBV_MA50'] = df['OBV'].rolling(50).mean()

clean_df = df.dropna()

if clean_df.empty:
    st.warning("⚠️ Calculating technicals... Waiting for complete data history.")
    st.stop()

latest = clean_df.iloc[-1]

# --- 3. SCORING REGIME LOGIC ---
buy_count, sell_count = 0, 0

# 1. Trend
if latest["MA50"] > latest["MA200"]:
    trend_status, trend_signal = "BULLISH", "🟢 BUY"
    buy_count += 1 
else: 
    trend_status, trend_signal = "BEARISH", "🔴 SELL"
    sell_count += 1

# 2. 200 DMA Stretch (Crypto Volatility Bounds: +/- 35%)
if latest["pct_vs_200ma"] <= -25:
    pct_status, pct_signal = "DEEP DISCOUNT", "🟢 BUY"
    buy_count += 1
elif latest["pct_vs_200ma"] >= 35:
    pct_status, pct_signal = "OVEREXTENDED", "🔴 SELL"
    sell_count += 1
else:
    pct_status, pct_signal = "NEUTRAL", "⚪ HOLD"

# 3. RSI
if latest["RSI14"] <= 30:
    rsi_status, rsi_signal = "OVERSOLD", "🟢 BUY"
    buy_count += 1
elif latest["RSI14"] >= 75:
    rsi_status, rsi_signal = "OVERBOUGHT", "🔴 SELL"
    sell_count += 1
else:
    rsi_status, rsi_signal = "NEUTRAL", "⚪ HOLD"

# 4. Bollinger %B
if latest["BB_pctB"] <= 0:
    bb_status, bb_signal = "BELOW LOWER BAND", "🟢 BUY"
    buy_count += 1
elif latest["BB_pctB"] >= 1:
    bb_status, bb_signal = "ABOVE UPPER BAND", "🔴 SELL"
    sell_count += 1
else:
    bb_status, bb_signal = "WITHIN BANDS", "⚪ HOLD"

# 5. MACD (13, 21)
if latest["MACD"] > latest["MACD_Signal"]:
    macd_status, macd_signal = "BULLISH CROSS", "🟢 BUY"
    buy_count += 1
else:
    macd_status, macd_signal = "BEARISH CROSS", "🔴 SELL"
    sell_count += 1

# 6. OBV Trend
if latest["OBV"] > latest["OBV_MA50"]:
    obv_status, obv_signal = "ACCUMULATION", "🟢 BUY"
    buy_count += 1
else:
    obv_status, obv_signal = "DISTRIBUTION", "🔴 SELL"
    sell_count += 1

# Verdict (Requires 4/6 Consensus)
if buy_count >= 4:
    verdict = "AGGRESSIVE BUY ZONE"
    color = "normal"
elif sell_count >= 4:
    verdict = "HEAVY DISTRIBUTION ZONE"
    color = "inverse"
else:
    verdict = "MIXED / NEUTRAL REGIME"
    color = "off"

# --- 4. DASHBOARD UI & RECOMMENDATION ---
st.divider()

col1, col2, col3 = st.columns(3)
col1.metric("Live Price", f"${latest['Close']:,.2f}")
col2.metric("Trend (50 vs 200)", trend_status)
col3.metric("Fibonacci MACD", macd_status)

col4, col5, col6 = st.columns(3)
col4.metric("% vs 200 DMA", f"{latest['pct_vs_200ma']:+.2f}%")
col5.metric("RSI (14)", f"{latest['RSI14']:.1f}")
col6.metric("OBV vs 50MA", obv_status)

# --- ALGORITHMIC VERDICT (FULLY FREE & OPEN) ---
st.divider()
st.subheader("🤖 Algorithmic Verdict")
st.write("Our quantitative engine has evaluated all active macro indicators for this asset.")

# 🟢 UNLOCKED FOR EVERYONE: Display the real consensus signal
if buy_count >= 4:
    st.success(f"🟢 **MACRO BUY ZONE** — Indicator Consensus: {buy_count} Buy Signals Aligned")
elif sell_count >= 4:
    st.error(f"🔴 **MACRO SELL ZONE** — Indicator Consensus: {sell_count} Sell Signals Aligned")
else:
    st.info(f"⚪ **NEUTRAL REGIME** — Consensus Mixed ({buy_count} Buy / {sell_count} Sell). Wait for alignment.")

# --- OPTIONAL SUPPORT / DONATION BANNER ---
st.write("")
st.markdown("""
<div style='background-color: #1E2127; padding: 20px; border-radius: 10px; border: 1px solid #333; text-align: center;'>
    <p style='color: #AAA; font-size: 14px; margin-bottom: 10px;'>💡 <i>YS Investment Research is provided free as an open quantitative project. If this model helps your portfolio, consider supporting the data feeds:</i></p>
    <a href="https://trakteer.id/yourname" target="_blank" style='background-color: #E5A937; color: #000; text-decoration: none; padding: 8px 16px; border-radius: 5px; font-weight: bold; font-size: 14px;'>☕ Support / Donate</a>
</div>
""", unsafe_allow_html=True)

st.subheader(f"Algorithmic Recommendation ({buy_count} Buy / {sell_count} Sell)")
if verdict == "AGGRESSIVE BUY ZONE":
    st.success(f"**🟢 {verdict}:** Strong structural alignment across price, momentum, and volume. Optimal cyclical entry.")
elif verdict == "HEAVY DISTRIBUTION ZONE":
    st.error(f"**🔴 {verdict}:** Market is structurally overextended with deteriorating momentum and volume flow. Protect capital.")
else:
    st.info(f"**⚪ {verdict}:** Conflicting signals between trend and momentum. Wait for a clear majority breakout.")

with st.expander("📊 View Detailed Indicator Breakdown", expanded=False):
    matrix_data = {
        "Indicator": ["Trend (50 vs 200)", "Deviation from 200 DMA", "RSI (14)", "Bollinger %B", "Custom MACD (13, 21)", "On-Balance Volume"],
        "Current Value": [f"50DMA: ${latest['MA50']:,.0f}", f"{latest['pct_vs_200ma']:+.2f}%", f"{latest['RSI14']:.1f}", f"{latest['BB_pctB']:.2f}", f"{latest['MACD']:,.0f}", "Live Data"],
        "Condition": [trend_status, pct_status, rsi_status, bb_status, macd_status, obv_status],
        "Signal": [trend_signal, pct_signal, rsi_signal, bb_signal, macd_signal, obv_signal]
    }
    st.table(pd.DataFrame(matrix_data))

st.divider()

# --- 5. TIMEFRAME SELECTOR & INTERACTIVE CHARTS ---
st.subheader("Macro Price Action & Technicals")

timeframe = st.radio("Select Chart Timeframe:", ["3 Months", "6 Months", "1 Year", "2 Years", "5 Years", "Max"], horizontal=True, index=5)

end_date = clean_df.index.max()
if timeframe == "3 Months": start_date = end_date - pd.DateOffset(months=3)
elif timeframe == "6 Months": start_date = end_date - pd.DateOffset(months=6)
elif timeframe == "1 Year": start_date = end_date - pd.DateOffset(years=1)
elif timeframe == "2 Years": start_date = end_date - pd.DateOffset(years=2)
elif timeframe == "5 Years": start_date = end_date - pd.DateOffset(years=5)
else: start_date = clean_df.index.min()

plot_df = clean_df[clean_df.index >= start_date]

# Main Price Chart
fig_price = go.Figure()
fig_price.add_trace(go.Candlestick(x=plot_df.index, open=plot_df['Open'], high=plot_df['High'], low=plot_df['Low'], close=plot_df['Close'], name='BTC'))
fig_price.add_trace(go.Scatter(x=plot_df.index, y=plot_df['MA50'], line=dict(color='orange', width=1.5), name='50-Day MA'))
fig_price.add_trace(go.Scatter(x=plot_df.index, y=plot_df['MA200'], line=dict(color='#00FFFF', width=2), name='200-Day MA (Cyan)'))
fig_price.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=500, margin=dict(l=10, r=10, t=30, b=10))
st.plotly_chart(fig_price, use_container_width=True)

# Sub-Charts Grid (4 Columns)
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.subheader("200 DMA Deviation (%)")
    fig_dma = go.Figure()
    fig_dma.add_trace(go.Scatter(x=plot_df.index, y=plot_df['pct_vs_200ma'], line=dict(color='#00FFFF', width=1.5), name='% vs 200DMA'))
    fig_dma.add_hline(y=35, line_dash="dash", line_color="red", annotation_text="+35%")
    fig_dma.add_hline(y=-25, line_dash="dash", line_color="green", annotation_text="-25%")
    fig_dma.add_hline(y=0, line_dash="dot", line_color="gray")
    fig_dma.update_layout(template="plotly_dark", height=280, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_dma, use_container_width=True)

with col_chart2:
    st.subheader("Relative Strength Index (RSI)")
    fig_rsi = go.Figure()
    fig_rsi.add_trace(go.Scatter(x=plot_df.index, y=plot_df['RSI14'], line=dict(color='purple', width=1.5), name='RSI (14)'))
    fig_rsi.add_hline(y=75, line_dash="dash", line_color="red", annotation_text="75")
    fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="30")
    fig_rsi.update_layout(template="plotly_dark", height=280, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_rsi, use_container_width=True)

col_chart3, col_chart4 = st.columns(2)

with col_chart3:
    st.subheader("MACD (13, 21)")
    fig_macd = go.Figure()
    fig_macd.add_trace(go.Scatter(x=plot_df.index, y=plot_df['MACD'], line=dict(color='blue', width=1.5), name='MACD Line'))
    fig_macd.add_trace(go.Scatter(x=plot_df.index, y=plot_df['MACD_Signal'], line=dict(color='orange', width=1.5), name='Signal Line'))
    fig_macd.add_bar(x=plot_df.index, y=plot_df['MACD'] - plot_df['MACD_Signal'], name='Histogram', marker_color='gray')
    fig_macd.update_layout(template="plotly_dark", height=280, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_macd, use_container_width=True)

with col_chart4:
    st.subheader("On-Balance Volume (OBV)")
    fig_obv = go.Figure()
    fig_obv.add_trace(go.Scatter(x=plot_df.index, y=plot_df['OBV'], line=dict(color='white', width=1.5), name='OBV'))
    fig_obv.add_trace(go.Scatter(x=plot_df.index, y=plot_df['OBV_MA50'], line=dict(color='orange', dash='dot', width=1.5), name='50MA'))
    fig_obv.update_layout(template="plotly_dark", height=280, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_obv, use_container_width=True)
