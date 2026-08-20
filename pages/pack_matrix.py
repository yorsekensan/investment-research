import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from disclaimer import render_disclaimer

# ==========================================
# ⚙️ ASSET CONFIGURATION
# ==========================================
PAGE_TITLE = "PACK (Small Cap / Rights Issue)"
PAGE_ICON = "📦"
TICKER = "PACK.JK"
DESCRIPTION = "Live quantitative tracking of packaging manufacturing dynamics. Includes USD/IDR Currency Margin Expansion and Sector Rotation vs IHSG."

st.set_page_config(page_title=f"{PAGE_TITLE} Matrix", page_icon=PAGE_ICON, layout="wide")

st.title(f"{PAGE_ICON} {PAGE_TITLE} Macro Matrix")
st.write(DESCRIPTION)
render_disclaimer()
st.divider()

# --- 1. DATA FETCHING (PACK, IHSG, USD/IDR) ---
@st.cache_data(ttl=3600)
def fetch_custom_data():
    df_PACK = yf.download(TICKER, period="max", progress=False)
    if isinstance(df_PACK.columns, pd.MultiIndex):
        df_PACK.columns = df_PACK.columns.droplevel(1)
        
    df_ihsg = yf.download("^JKSE", period="max", progress=False)
    if isinstance(df_ihsg.columns, pd.MultiIndex):
        df_ihsg.columns = df_ihsg.columns.droplevel(1)
        
    df_idr = yf.download("IDR=X", period="max", progress=False)
    if isinstance(df_idr.columns, pd.MultiIndex):
        df_idr.columns = df_idr.columns.droplevel(1)

    # 1. PACK Technical Indicators
    df_PACK['SMA_50'] = df_PACK['Close'].rolling(window=50).mean()
    df_PACK['SMA_200'] = df_PACK['Close'].rolling(window=200).mean()
    
    # RSI (14)
    delta = df_PACK['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df_PACK['RSI'] = 100 - (100 / (1 + (gain / loss)))
    
    # Fast MACD (13, 21 settings)
    exp1 = df_PACK['Close'].ewm(span=13, adjust=False).mean()
    exp2 = df_PACK['Close'].ewm(span=21, adjust=False).mean()
    df_PACK['MACD'] = exp1 - exp2
    df_PACK['Signal_Line'] = df_PACK['MACD'].ewm(span=9, adjust=False).mean()
    df_PACK['MACD_Hist'] = df_PACK['MACD'] - df_PACK['Signal_Line']
    
    # 2. USD/IDR FX Indicator
    df_idr['SMA_50'] = df_idr['Close'].rolling(window=50).mean()
    
    # 3. Relative Strength (20-Day Return vs IHSG)
    PACK_20d = (df_PACK['Close'].iloc[-1] - df_PACK['Close'].iloc[-20]) / df_PACK['Close'].iloc[-20] * 100
    ihsg_20d = (df_ihsg['Close'].iloc[-1] - df_ihsg['Close'].iloc[-20]) / df_ihsg['Close'].iloc[-20] * 100

    return df_PACK.dropna(), df_idr.dropna(), PACK_20d, ihsg_20d

try:
    df, df_idr, PACK_20d, ihsg_20d = fetch_custom_data()
except Exception as e:
    st.error("Failed to fetch live macro data. Yahoo Finance might be rate-limiting.")
    st.stop()

current_price = float(df['Close'].iloc[-1])
current_rsi = float(df['RSI'].iloc[-1])
current_macd = float(df['MACD'].iloc[-1])
current_signal = float(df['Signal_Line'].iloc[-1])
current_idr = float(df_idr['Close'].iloc[-1])
idr_sma50 = float(df_idr['SMA_50'].iloc[-1])

# --- 2. HIERARCHICAL CONVICTION SCORING ---
conviction_score = 0
indicators = []

def add_indicator(metric, weight, value, signal, explanation):
    indicators.append({
        "Metric": metric, 
        "Weight": weight,
        "Current Value": value, 
        "Signal": signal, 
        "How to Read": explanation
    })

# Core Regime Boolean
is_bull_regime = pd.notna(df['SMA_200'].iloc[-1]) and (current_price > df['SMA_200'].iloc[-1])

# Ind 1: Price vs 200 SMA (Weight: 30%)
if pd.notna(df['SMA_200'].iloc[-1]):
    if current_price > df['SMA_200'].iloc[-1]:
        conviction_score += 30
        add_indicator("Long-Term Trend (200 SMA)", "30%", "Price Above 200 SMA", "🟢 Buy", "Primary regime filter. Price > 200 SMA dictates a structural manufacturing bull cycle.")
    else:
        add_indicator("Long-Term Trend (200 SMA)", "30%", "Price Below 200 SMA", "🔴 Sell", "Primary regime filter. Price < 200 SMA dictates a structural contraction cycle.")
else:
    add_indicator("Long-Term Trend (200 SMA)", "30%", "Data Unavailable", "⚪ Neutral", "Awaiting sufficient historical data.")

# Ind 2: Currency Tailwind (USD/IDR vs 50 SMA) (Weight: 25%)
if pd.notna(current_idr) and pd.notna(idr_sma50):
    if current_idr < idr_sma50:
        conviction_score += 25
        add_indicator("Currency Tailwind (USD/IDR vs 50 SMA)", "25%", f"Rp {current_idr:,.0f}", "🟢 Buy", "Strengthening Rupiah lowers imported raw material costs, expanding packaging profit margins.")
    else:
        add_indicator("Currency Tailwind (USD/IDR vs 50 SMA)", "25%", f"Rp {current_idr:,.0f}", "🔴 Sell", "Weakening Rupiah increases COGS (Cost of Goods Sold) for raw manufacturing materials.")
else:
    add_indicator("Currency Tailwind (USD/IDR vs 50 SMA)", "25%", "Data Unavailable", "⚪ Neutral", "Awaiting sufficient historical data.")

# Ind 3: Sector Rotation / Relative Strength (Weight: 20%)
if pd.notna(PACK_20d) and pd.notna(ihsg_20d):
    if PACK_20d > ihsg_20d:
        conviction_score += 20
        add_indicator("Sector Rotation (vs IHSG 20d)", "20%", f"PACK > IHSG", "🟢 Buy", "Outperforming the broader benchmark signals smart money rotation into this specific small-cap/rights issue.")
    else:
        add_indicator("Sector Rotation (vs IHSG 20d)", "20%", f"PACK < IHSG", "🔴 Sell", "Underperforming the index indicates capital is ignoring this asset in the current cycle.")
else:
    add_indicator("Sector Rotation (vs IHSG 20d)", "20%", "Data Unavailable", "⚪ Neutral", "Awaiting sufficient historical data.")

# Ind 4: Price vs 50 SMA (Weight: 10%)
if pd.notna(df['SMA_50'].iloc[-1]):
    if current_price > df['SMA_50'].iloc[-1]:
        conviction_score += 10
        add_indicator("Medium-Term Trend (50 SMA)", "10%", "Price Above 50 SMA", "🟢 Buy", "Shows strong quarterly momentum and sustained buying interest.")
    else:
        add_indicator("Medium-Term Trend (50 SMA)", "10%", "Price Below 50 SMA", "🔴 Sell", "Shows quarterly trend deceleration and loss of buying pressure.")
else:
    add_indicator("Medium-Term Trend (50 SMA)", "10%", "Data Unavailable", "⚪ Neutral", "Awaiting sufficient historical data.")

# Ind 5: Trend Velocity MACD (Weight: 10%)
if pd.notna(current_macd) and pd.notna(current_signal):
    if current_macd > current_signal:
        conviction_score += 10
        add_indicator("Trend Velocity (MACD 13,21)", "10%", "MACD > Signal", "🟢 Buy", "Short-term bullish momentum acceleration.")
    else:
        add_indicator("Trend Velocity (MACD 13,21)", "10%", "MACD < Signal", "🔴 Sell", "Short-term trend exhaustion and downside momentum.")
else:
    add_indicator("Trend Velocity (MACD 13,21)", "10%", "Data Unavailable", "⚪ Neutral", "Awaiting sufficient historical data.")

# Ind 6: Momentum RSI (Weight: 5%)
if pd.notna(current_rsi):
    if current_rsi < 40:
        if is_bull_regime:
            conviction_score += 5
            add_indicator("Momentum Oscillator (RSI)", "5%", f"RSI at {current_rsi:.1f}", "🟢 Buy (Dip)", "Oversold during a macro bull regime. High probability dip-buy zone.")
        else:
            add_indicator("Momentum Oscillator (RSI)", "5%", f"RSI at {current_rsi:.1f}", "🔴 Sell (Falling Knife)", "Oversold during a macro bear regime. Avoid catching a falling knife.")
    elif current_rsi > 60:
        add_indicator("Momentum Oscillator (RSI)", "5%", f"RSI at {current_rsi:.1f}", "🔴 Sell (Overbought)", "Overextended short-term buying, prone to sharp momentum pullbacks.")
    else:
        add_indicator("Momentum Oscillator (RSI)", "5%", f"RSI at {current_rsi:.1f}", "⚪ Neutral", "Balanced momentum without cyclical exhaustion.")
else:
    add_indicator("Momentum Oscillator (RSI)", "5%", "Data Unavailable", "⚪ Neutral", "Awaiting sufficient historical data.")

# --- 3. DASHBOARD UI LAYOUT & CHARTS ---
col1, col2 = st.columns([2.5, 1])

timeframe_selector = dict(
    buttons=list([
        dict(count=3, label="3M", step="month", stepmode="backward"),
        dict(count=6, label="6M", step="month", stepmode="backward"),
        dict(count=1, label="1Y", step="year", stepmode="backward"),
        dict(count=2, label="2Y", step="year", stepmode="backward"),
        dict(count=3, label="3Y", step="year", stepmode="backward"),
        dict(count=5, label="5Y", step="year", stepmode="backward"),
        dict(step="all", label="All")
    ]),
    bgcolor="#1E2127",
    activecolor="#E5A937",
    font=dict(color="#FFFFFF", size=11),
    x=0.0,
    y=1.15
)

with col1:
    tab1, tab2, tab3 = st.tabs(["📈 Price & SMAs", "⚡ RSI Oscillator", "📊 MACD (13,21)"])
    
    with tab1:
        fig_price = go.Figure()
        fig_price.add_trace(go.Scatter(x=df.index, y=df['Close'], name='PACK Price', line=dict(color='#2ECC71', width=2)))
        fig_price.add_trace(go.Scatter(x=df.index, y=df['SMA_200'], name='200 SMA', line=dict(color='white', width=1, dash='dash')))
        fig_price.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], name='50 SMA', line=dict(color='#E5A937', width=1)))
        
        fig_price.update_xaxes(rangeselector=timeframe_selector, type="date")
        fig_price.update_layout(template="plotly_dark", height=420, margin=dict(l=0, r=0, t=50, b=0), plot_bgcolor='#0E1117', paper_bgcolor='#0E1117')
        st.plotly_chart(fig_price, use_container_width=True)
        
    with tab2:
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI (14)', line=dict(color='#9B59B6', width=2)))
        fig_rsi.add_hline(y=60, line_dash="dash", line_color="red")
        fig_rsi.add_hline(y=40, line_dash="dash", line_color="green")
        
        fig_rsi.update_xaxes(rangeselector=timeframe_selector, type="date")
        fig_rsi.update_layout(template="plotly_dark", height=420, margin=dict(l=0, r=0, t=50, b=0), plot_bgcolor='#0E1117', paper_bgcolor='#0E1117')
        st.plotly_chart(fig_rsi, use_container_width=True)

    with tab3:
        fig_macd = go.Figure()
        fig_macd.add_trace(go.Scatter(x=df.index, y=df['MACD'], name='MACD (13,21)', line=dict(color='#3498DB', width=1.5)))
        fig_macd.add_trace(go.Scatter(x=df.index, y=df['Signal_Line'], name='Signal', line=dict(color='#E67E22', width=1.5)))
        colors = ['#2ECC71' if val >= 0 else '#E74C3C' for val in df['MACD_Hist']]
        fig_macd.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], name='Histogram', marker_color=colors))
        
        fig_macd.update_xaxes(rangeselector=timeframe_selector, type="date")
        fig_macd.update_layout(template="plotly_dark", height=420, margin=dict(l=0, r=0, t=50, b=0), plot_bgcolor='#0E1117', paper_bgcolor='#0E1117')
        st.plotly_chart(fig_macd, use_container_width=True)

with col2:
    st.subheader("Live Metrics")
    st.metric("PACK Price", f"Rp {current_price:,.0f}")
    st.metric("USD/IDR Exchange", f"Rp {current_idr:,.0f}")
    
    ihsg_color = "normal" if PACK_20d > ihsg_20d else "inverse"
    st.metric("20D Rel. Leadership", f"{PACK_20d:.1f}%", delta=f"{PACK_20d - ihsg_20d:.1f}% vs IHSG", delta_color=ihsg_color)

# --- 4. ALGORITHMIC RECOMMENDATION ---
st.divider()

st.subheader(f"Algorithmic Conviction Score: {conviction_score}%")

# Progress bar visual
st.progress(conviction_score / 100.0)

if conviction_score >= 60:
    st.success(f"🟢 **MACRO BULL ENGINE (Score: {conviction_score}%):** Structural manufacturing tailwinds and currency expansion are aligned. Favorable regime.")
elif conviction_score < 40:
    st.error(f"🔴 **SEVERE BEAR MARKET (Score: {conviction_score}%):** Structural contraction and margin compression. Defensive stance required.")
else:
    st.info(f"⚪ **NEUTRAL / SIDEWAYS CHOP (Score: {conviction_score}%):** Mixed momentum signals. High risk of choppy whipsaws. Stand aside.")

with st.expander("📊 View Detailed Indicator Weights & Breakdown", expanded=True):
    st.table(pd.DataFrame(indicators))

st.write("")

# Support / Donate Banner
st.markdown("""
<div style='background-color: #1E2127; padding: 20px; border-radius: 10px; border: 1px solid #333; text-align: center;'>
    <p style='color: #AAA; font-size: 14px; margin-bottom: 10px;'>💡 <i>YS Investment Research is provided free as an open quantitative project. If this model helps your portfolio, consider supporting the data feeds:</i></p>
    <a href="https://trakteer.id/yourname" target="_blank" style='background-color: #E5A937; color: #000; text-decoration: none; padding: 8px 16px; border-radius: 5px; font-weight: bold; font-size: 14px;'>☕ Support / Donate</a>
</div>
""", unsafe_allow_html=True)
