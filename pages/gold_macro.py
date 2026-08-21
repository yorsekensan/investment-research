import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from disclaimer import render_disclaimer

# ==========================================
# ⚙️ ASSET CONFIGURATION
# ==========================================
PAGE_TITLE = "Gold (Safe Haven)"
PAGE_ICON = "🪙"
TICKER = "GC=F"
DESCRIPTION = "Live quantitative tracking of safe-haven commodities. Includes Global USD (DXY) and US 10Y Yield Macro Dynamics."

st.set_page_config(page_title=f"{PAGE_TITLE} Matrix", page_icon=PAGE_ICON, layout="wide")

st.title(f"{PAGE_ICON} {PAGE_TITLE} Macro Matrix")
st.write(DESCRIPTION)
render_disclaimer()
st.divider()

# --- 1. DATA FETCHING (Gold, DXY, US10Y) ---
@st.cache_data(ttl=3600)
def fetch_custom_data():
    df_gold = yf.download(TICKER, period="max", progress=False)
    if isinstance(df_gold.columns, pd.MultiIndex):
        df_gold.columns = df_gold.columns.droplevel(1)
        
    df_dxy = yf.download("DX-Y.NYB", period="max", progress=False)
    if isinstance(df_dxy.columns, pd.MultiIndex):
        df_dxy.columns = df_dxy.columns.droplevel(1)
        
    df_tnx = yf.download("^TNX", period="max", progress=False)
    if isinstance(df_tnx.columns, pd.MultiIndex):
        df_tnx.columns = df_tnx.columns.droplevel(1)

    # 1. Gold Technical Indicators
    df_gold['SMA_50'] = df_gold['Close'].rolling(window=50).mean()
    df_gold['SMA_200'] = df_gold['Close'].rolling(window=200).mean()
    
    # RSI (14)
    delta = df_gold['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df_gold['RSI'] = 100 - (100 / (1 + (gain / loss)))
    
    # Fast MACD (13, 21 settings)
    exp1 = df_gold['Close'].ewm(span=13, adjust=False).mean()
    exp2 = df_gold['Close'].ewm(span=21, adjust=False).mean()
    df_gold['MACD'] = exp1 - exp2
    df_gold['Signal_Line'] = df_gold['MACD'].ewm(span=9, adjust=False).mean()
    df_gold['MACD_Hist'] = df_gold['MACD'] - df_gold['Signal_Line']
    
    # 2. DXY Indicator
    df_dxy['SMA_50'] = df_dxy['Close'].rolling(window=50).mean()
    
    # 3. US 10Y Yield Indicator
    df_tnx['SMA_50'] = df_tnx['Close'].rolling(window=50).mean()

    return df_gold.dropna(), df_dxy.dropna(), df_tnx.dropna()

try:
    df, df_dxy, df_tnx = fetch_custom_data()
except Exception as e:
    st.error("Failed to fetch live macro data. Yahoo Finance might be rate-limiting.")
    st.stop()

current_price = float(df['Close'].iloc[-1])
current_rsi = float(df['RSI'].iloc[-1])
current_macd = float(df['MACD'].iloc[-1])
current_signal = float(df['Signal_Line'].iloc[-1])
current_dxy = float(df_dxy['Close'].iloc[-1])
dxy_sma50 = float(df_dxy['SMA_50'].iloc[-1])
current_tnx = float(df_tnx['Close'].iloc[-1])
tnx_sma50 = float(df_tnx['SMA_50'].iloc[-1])

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
        add_indicator("Long-Term Trend (200 SMA)", "30%", "Price Above 200 SMA", "🟢 Buy", "Primary regime filter. Price > 200 SMA confirms a structural precious metals bull market.")
    else:
        add_indicator("Long-Term Trend (200 SMA)", "30%", "Price Below 200 SMA", "🔴 Sell", "Primary regime filter. Price < 200 SMA confirms a structural bear trend or macro consolidation.")
else:
    add_indicator("Long-Term Trend (200 SMA)", "30%", "Data Unavailable", "⚪ Neutral", "Awaiting sufficient historical data.")

# Ind 2: Global USD Debasement (DXY vs 50 SMA) (Weight: 25%)
if pd.notna(current_dxy) and pd.notna(dxy_sma50):
    if current_dxy < dxy_sma50:
        conviction_score += 25
        add_indicator("USD Debasement (DXY vs 50 SMA)", "25%", f"DXY at {current_dxy:.2f}", "🟢 Buy", "Weak US Dollar boosts Gold's purchasing power appeal as a global store of value.")
    else:
        add_indicator("USD Debasement (DXY vs 50 SMA)", "25%", f"DXY at {current_dxy:.2f}", "🔴 Sell", "Strong US Dollar creates a direct valuation headwind for fiat-priced precious metals.")
else:
    add_indicator("USD Debasement (DXY vs 50 SMA)", "25%", "Data Unavailable", "⚪ Neutral", "Awaiting sufficient historical data.")

# Ind 3: Opportunity Cost (US10Y Yield vs 50 SMA) (Weight: 20%)
if pd.notna(current_tnx) and pd.notna(tnx_sma50):
    if current_tnx < tnx_sma50:
        conviction_score += 20
        add_indicator("Opportunity Cost (US10Y vs 50 SMA)", "20%", f"Yield at {current_tnx:.2f}%", "🟢 Buy", "Easing bond yields reduce the opportunity cost of holding non-yielding assets like Gold.")
    else:
        add_indicator("Opportunity Cost (US10Y vs 50 SMA)", "20%", f"Yield at {current_tnx:.2f}%", "🔴 Sell", "Rising bond yields increase the opportunity cost relative to interest-bearing Treasuries.")
else:
    add_indicator("Opportunity Cost (US10Y vs 50 SMA)", "20%", "Data Unavailable", "⚪ Neutral", "Awaiting sufficient historical data.")

# Ind 4: Price vs 50 SMA (Weight: 10%)
if pd.notna(df['SMA_50'].iloc[-1]):
    if current_price > df['SMA_50'].iloc[-1]:
        conviction_score += 10
        add_indicator("Medium-Term Trend (50 SMA)", "10%", "Price Above 50 SMA", "🟢 Buy", "Signals strong medium-term safe-haven demand and tactical momentum.")
    else:
        add_indicator("Medium-Term Trend (50 SMA)", "10%", "Price Below 50 SMA", "🔴 Sell", "Signals medium-term trend deceleration and tactical profit-taking.")
else:
    add_indicator("Medium-Term Trend (50 SMA)", "10%", "Data Unavailable", "⚪ Neutral", "Awaiting sufficient historical data.")

# Ind 5: Trend Velocity MACD (Weight: 10%)
if pd.notna(current_macd) and pd.notna(current_signal):
    if current_macd > current_signal:
        conviction_score += 10
        add_indicator("Trend Velocity (MACD 13,21)", "10%", "MACD > Signal", "🟢 Buy", "Short-term bullish trend acceleration.")
    else:
        add_indicator("Trend Velocity (MACD 13,21)", "10%", "MACD < Signal", "🔴 Sell", "Short-term momentum weakness.")
else:
    add_indicator("Trend Velocity (MACD 13,21)", "10%", "Data Unavailable", "⚪ Neutral", "Awaiting sufficient historical data.")

# Ind 6: Momentum RSI (Weight: 5%)
if pd.notna(current_rsi):
    if current_rsi < 40:
        if is_bull_regime:
            conviction_score += 5
            add_indicator("Momentum Oscillator (RSI)", "5%", f"RSI at {current_rsi:.1f}", "🟢 Buy (Dip)", "Oversold during a macro bull regime. High probability entry point.")
        else:
            add_indicator("Momentum Oscillator (RSI)", "5%", f"RSI at {current_rsi:.1f}", "🔴 Sell (Falling Knife)", "Oversold during a macro bear regime. High risk of continued structural breakdown.")
    elif current_rsi > 60:
        add_indicator("Momentum Oscillator (RSI)", "5%", f"RSI at {current_rsi:.1f}", "🔴 Sell (Overbought)", "Overbought conditions prone to short-term mean reversion.")
    else:
        add_indicator("Momentum Oscillator (RSI)", "5%", f"RSI at {current_rsi:.1f}", "⚪ Neutral", "Balanced safe-haven demand without momentum extremes.")
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
    activecolor="#E5A937"
)

with col1:
    tab1, tab2, tab3 = st.tabs(["📈 Price & SMAs", "⚡ RSI Oscillator", "📊 MACD (13,21)"])
    
    with tab1:
        fig_price = go.Figure()
        fig_price.add_trace(go.Scatter(x=df.index, y=df['Close'], name='Gold Price', line=dict(color='#E5A937', width=2)))
        fig_price.add_trace(go.Scatter(x=df.index, y=df['SMA_200'], name='200 SMA', line=dict(color='white', width=1, dash='dash')))
        fig_price.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], name='50 SMA', line=dict(color='#00529b', width=1)))
        
        fig_price.update_xaxes(rangeselector=timeframe_selector)
        fig_price.update_layout(template="plotly_dark", height=400, margin=dict(l=0, r=0, t=20, b=0), plot_bgcolor='#0E1117', paper_bgcolor='#0E1117')
        st.plotly_chart(fig_price, use_container_width=True)
        
    with tab2:
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI (14)', line=dict(color='#9B59B6', width=2)))
        fig_rsi.add_hline(y=60, line_dash="dash", line_color="red")
        fig_rsi.add_hline(y=40, line_dash="dash", line_color="green")
        
        fig_rsi.update_xaxes(rangeselector=timeframe_selector)
        fig_rsi.update_layout(template="plotly_dark", height=400, margin=dict(l=0, r=0, t=20, b=0), plot_bgcolor='#0E1117', paper_bgcolor='#0E1117')
        st.plotly_chart(fig_rsi, use_container_width=True)

    with tab3:
        fig_macd = go.Figure()
        fig_macd.add_trace(go.Scatter(x=df.index, y=df['MACD'], name='MACD (13,21)', line=dict(color='#3498DB', width=1.5)))
        fig_macd.add_trace(go.Scatter(x=df.index, y=df['Signal_Line'], name='Signal', line=dict(color='#E67E22', width=1.5)))
        colors = ['#2ECC71' if val >= 0 else '#E74C3C' for val in df['MACD_Hist']]
        fig_macd.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], name='Histogram', marker_color=colors))
        
        fig_macd.update_xaxes(rangeselector=timeframe_selector)
        fig_macd.update_layout(template="plotly_dark", height=400, margin=dict(l=0, r=0, t=20, b=0), plot_bgcolor='#0E1117', paper_bgcolor='#0E1117')
        st.plotly_chart(fig_macd, use_container_width=True)

with col2:
    st.subheader("Live Metrics")
    st.metric("Gold Price (/oz)", f"${current_price:,.2f}")
    st.metric("DXY Dollar Index", f"{current_dxy:.2f}")
    st.metric("US 10Y Yield", f"{current_tnx:.2f}%")

# --- 4. ALGORITHMIC RECOMMENDATION ---
st.divider()

st.subheader(f"Algorithmic Conviction Score: {conviction_score}%")

# Progress bar visual
st.progress(conviction_score / 100.0)

if conviction_score >= 70:
    st.success(f"🟢 **MACRO BULL ENGINE (Score: {conviction_score}%):** Structural safe-haven demand and opportunity costs are aligned. Favorable regime.")
elif conviction_score < 30:
    st.error(f"🔴 **SEVERE BEAR MARKET (Score: {conviction_score}%):** Rising yields and a strong dollar are draining capital from precious metals.")
else:
    st.info(f"⚪ **NEUTRAL / SIDEWAYS CHOP (Score: {conviction_score}%):** Conflicting macro signals. Wait for structural alignment in rates and FX.")

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
