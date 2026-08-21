import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from disclaimer import render_disclaimer

# ==========================================
# ⚙️ ASSET CONFIGURATION
# ==========================================
PAGE_TITLE = "Bitcoin (High Beta)"
PAGE_ICON = "📈"
TICKER = "BTC-USD"
DESCRIPTION = "Live quantitative tracking of high-beta digital assets. Includes Global USD (DXY) Liquidity and S&P 500 Relative Strength."

st.set_page_config(page_title=f"{PAGE_TITLE} Matrix", page_icon=PAGE_ICON, layout="wide")

st.title(f"{PAGE_ICON} {PAGE_TITLE} Macro Matrix")
st.write(DESCRIPTION)
render_disclaimer()
st.divider()

# --- 1. DATA FETCHING (BTC, DXY, S&P 500) ---
@st.cache_data(ttl=3600)
def fetch_custom_data():
    df_btc = yf.download(TICKER, period="max", progress=False)
    if isinstance(df_btc.columns, pd.MultiIndex):
        df_btc.columns = df_btc.columns.droplevel(1)
        
    df_dxy = yf.download("DX-Y.NYB", period="max", progress=False)
    if isinstance(df_dxy.columns, pd.MultiIndex):
        df_dxy.columns = df_dxy.columns.droplevel(1)
        
    df_spx = yf.download("^GSPC", period="max", progress=False)
    if isinstance(df_spx.columns, pd.MultiIndex):
        df_spx.columns = df_spx.columns.droplevel(1)

    # 1. BTC Technical Indicators
    df_btc['SMA_50'] = df_btc['Close'].rolling(window=50).mean()
    df_btc['SMA_200'] = df_btc['Close'].rolling(window=200).mean()
    
    # RSI (14)
    delta = df_btc['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df_btc['RSI'] = 100 - (100 / (1 + (gain / loss)))
    
    # Fast MACD (13, 21 settings)
    exp1 = df_btc['Close'].ewm(span=13, adjust=False).mean()
    exp2 = df_btc['Close'].ewm(span=21, adjust=False).mean()
    df_btc['MACD'] = exp1 - exp2
    df_btc['Signal_Line'] = df_btc['MACD'].ewm(span=9, adjust=False).mean()
    df_btc['MACD_Hist'] = df_btc['MACD'] - df_btc['Signal_Line']
    
    # 2. DXY Indicator
    df_dxy['SMA_50'] = df_dxy['Close'].rolling(window=50).mean()
    
    # 3. Relative Strength (20-Day Return vs SPX)
    btc_20d = (df_btc['Close'].iloc[-1] - df_btc['Close'].iloc[-20]) / df_btc['Close'].iloc[-20] * 100
    spx_20d = (df_spx['Close'].iloc[-1] - df_spx['Close'].iloc[-20]) / df_spx['Close'].iloc[-20] * 100

    return df_btc.dropna(), df_dxy.dropna(), btc_20d, spx_20d

try:
    df, df_dxy, btc_20d, spx_20d = fetch_custom_data()
except Exception as e:
    st.error("Failed to fetch live macro data. Yahoo Finance might be rate-limiting.")
    st.stop()

current_price = float(df['Close'].iloc[-1])
current_rsi = float(df['RSI'].iloc[-1])
current_macd = float(df['MACD'].iloc[-1])
current_signal = float(df['Signal_Line'].iloc[-1])
current_dxy = float(df_dxy['Close'].iloc[-1])
dxy_sma50 = float(df_dxy['SMA_50'].iloc[-1])

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
        add_indicator("Long-Term Trend (200 SMA)", "30%", "Price Above 200 SMA", "🟢 Buy", "Primary regime filter. Price > 200 SMA confirms a structural bull market regime and macro cycle expansion.")
    else:
        add_indicator("Long-Term Trend (200 SMA)", "30%", "Price Below 200 SMA", "🔴 Sell", "Primary regime filter. Price < 200 SMA confirms a structural bear market regime or deep macro correction.")
else:
    add_indicator("Long-Term Trend (200 SMA)", "30%", "Data Unavailable", "⚪ Neutral", "Awaiting sufficient historical data.")

# Ind 2: Global USD Liquidity (DXY vs 50 SMA) (Weight: 25%)
if pd.notna(current_dxy) and pd.notna(dxy_sma50):
    if current_dxy < dxy_sma50:
        conviction_score += 25
        add_indicator("Global USD Liquidity (DXY vs 50 SMA)", "25%", f"DXY at {current_dxy:.2f}", "🟢 Buy", "Weakening US Dollar index creates a macro liquidity tailwind for global high-beta assets.")
    else:
        add_indicator("Global USD Liquidity (DXY vs 50 SMA)", "25%", f"DXY at {current_dxy:.2f}", "🔴 Sell", "Strengthening US Dollar tightens global financial conditions and suppresses crypto liquidity.")
else:
    add_indicator("Global USD Liquidity (DXY vs 50 SMA)", "25%", "Data Unavailable", "⚪ Neutral", "Awaiting sufficient historical data.")

# Ind 3: Relative Risk Appetite (vs SPX 20d) (Weight: 20%)
if pd.notna(btc_20d) and pd.notna(spx_20d):
    if btc_20d > spx_20d:
        conviction_score += 20
        add_indicator("Relative Risk Appetite (vs SPX 20d)", "20%", f"BTC > SPX", "🟢 Buy", "BTC outperforming US equities signals aggressive global risk-on appetite and speculative inflows.")
    else:
        add_indicator("Relative Risk Appetite (vs SPX 20d)", "20%", f"BTC < SPX", "🔴 Sell", "BTC underperforming US equities signals risk-off hedging or capital flight to safety.")
else:
    add_indicator("Relative Risk Appetite (vs SPX 20d)", "20%", "Data Unavailable", "⚪ Neutral", "Awaiting sufficient historical data.")

# Ind 4: Price vs 50 SMA (Weight: 10%)
if pd.notna(df['SMA_50'].iloc[-1]):
    if current_price > df['SMA_50'].iloc[-1]:
        conviction_score += 10
        add_indicator("Medium-Term Trend (50 SMA)", "10%", "Price Above 50 SMA", "🟢 Buy", "Price > 50 SMA indicates strong medium-term buying momentum and key technical support.")
    else:
        add_indicator("Medium-Term Trend (50 SMA)", "10%", "Price Below 50 SMA", "🔴 Sell", "Price < 50 SMA indicates medium-term weakness and loss of momentum.")
else:
    add_indicator("Medium-Term Trend (50 SMA)", "10%", "Data Unavailable", "⚪ Neutral", "Awaiting sufficient historical data.")

# Ind 5: Trend Velocity MACD (Weight: 10%)
if pd.notna(current_macd) and pd.notna(current_signal):
    if current_macd > current_signal:
        conviction_score += 10
        add_indicator("Trend Velocity (MACD 13,21)", "10%", "MACD > Signal", "🟢 Buy", "MACD line above Signal line indicates short-term bullish momentum acceleration.")
    else:
        add_indicator("Trend Velocity (MACD 13,21)", "10%", "MACD < Signal", "🔴 Sell", "MACD line below Signal line indicates short-term bearish momentum deceleration.")
else:
    add_indicator("Trend Velocity (MACD 13,21)", "10%", "Data Unavailable", "⚪ Neutral", "Awaiting sufficient historical data.")

# Ind 6: Momentum RSI (Weight: 5%)
if pd.notna(current_rsi):
    if current_rsi < 40:
        if is_bull_regime:
            conviction_score += 5
            add_indicator("Momentum Oscillator (RSI)", "5%", f"RSI at {current_rsi:.1f}", "🟢 Buy (Dip)", "Oversold during a macro bull regime. High probability accumulation zone.")
        else:
            add_indicator("Momentum Oscillator (RSI)", "5%", f"RSI at {current_rsi:.1f}", "🔴 Sell (Falling Knife)", "Oversold during a macro bear regime. Do not attempt to catch the falling knife.")
    elif current_rsi > 60:
        add_indicator("Momentum Oscillator (RSI)", "5%", f"RSI at {current_rsi:.1f}", "🔴 Sell (Overbought)", "Overbought conditions prone to sharp leverage flushes or corrections.")
    else:
        add_indicator("Momentum Oscillator (RSI)", "5%", f"RSI at {current_rsi:.1f}", "⚪ Neutral", "Healthy price action without extreme leverage overextension.")
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
        fig_price.add_trace(go.Scatter(x=df.index, y=df['Close'], name='BTC Price', line=dict(color='#F2A900', width=2)))
        fig_price.add_trace(go.Scatter(x=df.index, y=df['SMA_200'], name='200 SMA', line=dict(color='white', width=1, dash='dash')))
        fig_price.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], name='50 SMA', line=dict(color='#3498DB', width=1)))
        
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
    st.metric("BTC Price", f"${current_price:,.2f}")
    st.metric("DXY Dollar Index", f"{current_dxy:.2f}")
    
    spx_color = "normal" if btc_20d > spx_20d else "inverse"
    st.metric("20D Rel. Risk Sentiment", f"{btc_20d:.1f}%", delta=f"{btc_20d - spx_20d:.1f}% vs S&P500", delta_color=spx_color)

# --- 4. ALGORITHMIC RECOMMENDATION ---
st.divider()

st.subheader(f"Algorithmic Conviction Score: {conviction_score}%")

# Progress bar visual
st.progress(conviction_score / 100.0)

if conviction_score >= 70:
    st.success(f"🟢 **MACRO BULL ENGINE (Score: {conviction_score}%):** Structural risk-on liquidity is expanding. Favorable regime for high-beta deployment.")
elif conviction_score < 30:
    st.error(f"🔴 **SEVERE BEAR MARKET (Score: {conviction_score}%):** Liquidity drain and structural breakdown. Severe risk of capital wipeout.")
else:
    st.info(f"⚪ **NEUTRAL / SIDEWAYS CHOP (Score: {conviction_score}%):** Conflicting macro signals. Wait for liquidity and structural alignment.")

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
