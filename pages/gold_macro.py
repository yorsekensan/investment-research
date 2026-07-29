import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# ==========================================
# ⚙️ ASSET CONFIGURATION (Change these for each page)
# ==========================================
PAGE_TITLE = "Gold (GC=F)"
PAGE_ICON = "🪙"
TICKER = "GC=F"
DESCRIPTION = "Live quantitative tracking of safe-haven commodities."

st.set_page_config(page_title=f"{PAGE_TITLE} Matrix", page_icon=PAGE_ICON, layout="wide")

st.title(f"{PAGE_ICON} {PAGE_TITLE} Macro Matrix")
st.write(DESCRIPTION)
st.divider()

# --- 1. DATA FETCHING & INDICATORS ---
@st.cache_data(ttl=3600)
def fetch_and_calculate(ticker):
    df = yf.download(ticker, period="1y", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
        
    if df.empty:
        return None
        
    # Moving Averages
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()
    
    # RSI (14)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    return df.dropna()

df = fetch_and_calculate(TICKER)

if df is None or df.empty:
    st.error(f"Failed to fetch live data for {TICKER}. Yahoo Finance might be currently rate-limiting.")
    st.stop()

current_price = df['Close'].iloc[-1]

# --- 2. SIGNAL EVALUATION ---
buy_count = 0
sell_count = 0
indicators = []

# Indicator 1: Price vs 200 SMA
if current_price > df['SMA_200'].iloc[-1]:
    buy_count += 1
    indicators.append({"Metric": "Trend (Price vs 200 SMA)", "Current Value": "Price Above 200 SMA", "Signal": "🟢 Buy"})
else:
    sell_count += 1
    indicators.append({"Metric": "Trend (Price vs 200 SMA)", "Current Value": "Price Below 200 SMA", "Signal": "🔴 Sell"})

# Indicator 2: Golden/Death Cross
if df['SMA_50'].iloc[-1] > df['SMA_200'].iloc[-1]:
    buy_count += 1
    indicators.append({"Metric": "Momentum (50 SMA vs 200 SMA)", "Current Value": "Golden Cross (50 > 200)", "Signal": "🟢 Buy"})
else:
    sell_count += 1
    indicators.append({"Metric": "Momentum (50 SMA vs 200 SMA)", "Current Value": "Death Cross (50 < 200)", "Signal": "🔴 Sell"})

# Indicator 3: RSI
current_rsi = df['RSI'].iloc[-1]
if current_rsi < 40:
    buy_count += 1
    indicators.append({"Metric": "Overbought/Oversold (RSI 14)", "Current Value": f"RSI at {current_rsi:.1f}", "Signal": "🟢 Buy (Oversold)"})
elif current_rsi > 70:
    sell_count += 1
    indicators.append({"Metric": "Overbought/Oversold (RSI 14)", "Current Value": f"RSI at {current_rsi:.1f}", "Signal": "🔴 Sell (Overbought)"})
else:
    indicators.append({"Metric": "Overbought/Oversold (RSI 14)", "Current Value": f"RSI at {current_rsi:.1f}", "Signal": "⚪ Neutral"})

# Indicator 4: MACD
if df['MACD'].iloc[-1] > df['Signal_Line'].iloc[-1]:
    buy_count += 1
    indicators.append({"Metric": "Trend Momentum (MACD)", "Current Value": "MACD > Signal Line", "Signal": "🟢 Buy"})
else:
    sell_count += 1
    indicators.append({"Metric": "Trend Momentum (MACD)", "Current Value": "MACD < Signal Line", "Signal": "🔴 Sell"})

# --- 3. DASHBOARD UI LAYOUT ---
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Price Action & Moving Averages")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name='Price', line=dict(color='#E5A937', width=2)))
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_200'], name='200 SMA', line=dict(color='white', width=1, dash='dash')))
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], name='50 SMA', line=dict(color='#00529b', width=1)))
    fig.update_layout(template="plotly_dark", margin=dict(l=0, r=0, t=30, b=0), plot_bgcolor='#0E1117', paper_bgcolor='#0E1117', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Live Metrics")
    st.metric("Current Price", f"{current_price:,.2f}")
    st.metric("RSI (14)", f"{current_rsi:.1f}")
    macd_status = "Bullish" if df['MACD'].iloc[-1] > df['Signal_Line'].iloc[-1] else "Bearish"
    st.metric("MACD Status", macd_status)

# --- 4. ALGORITHMIC RECOMMENDATION (UI Exact Match) ---
st.divider()

st.subheader(f"Algorithmic Recommendation ({buy_count} Buy / {sell_count} Sell)")

if buy_count > sell_count:
    st.success("🟢 **MACRO BUY ZONE:** Trend and momentum indicators align bullish.")
elif sell_count > buy_count:
    st.error("🔴 **MACRO SELL ZONE:** Trend and momentum indicators align bearish.")
else:
    st.info("⚪ **MIXED / NEUTRAL REGIME:** Conflicting signals between trend and momentum. Wait for a clear majority breakout.")

with st.expander("📊 View Detailed Indicator Breakdown"):
    st.table(pd.DataFrame(indicators))

st.write("")

# Support / Donate Banner
st.markdown("""
<div style='background-color: #1E2127; padding: 20px; border-radius: 10px; border: 1px solid #333; text-align: center;'>
    <p style='color: #AAA; font-size: 14px; margin-bottom: 10px;'>💡 <i>YS Investment Research is provided free as an open quantitative project. If this model helps your portfolio, consider supporting the data feeds:</i></p>
    <a href="https://trakteer.id/yourname" target="_blank" style='background-color: #E5A937; color: #000; text-decoration: none; padding: 8px 16px; border-radius: 5px; font-weight: bold; font-size: 14px;'>☕ Support / Donate</a>
</div>
""", unsafe_allow_html=True)
