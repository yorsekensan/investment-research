import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# ==========================================
# ⚙️ ASSET CONFIGURATION
# ==========================================
PAGE_TITLE = "ADRO (Cyclical Energy)"
PAGE_ICON = "⛏️"
TICKER = "ADRO.JK"
DESCRIPTION = "Live quantitative tracking of cyclical energy dynamics. Includes USD/IDR Currency Margin Expansion and Sector Rotation vs IHSG."

st.set_page_config(page_title=f"{PAGE_TITLE} Matrix", page_icon=PAGE_ICON, layout="wide")

st.title(f"{PAGE_ICON} {PAGE_TITLE} Macro Matrix")
st.write(DESCRIPTION)
st.divider()

# --- 1. DATA FETCHING (ADRO, IHSG, USD/IDR) ---
@st.cache_data(ttl=3600)
def fetch_custom_data():
    # Fetch 'max' period to support 5Y and All-Time chart range selectors
    df_adro = yf.download(TICKER, period="max", progress=False)
    if isinstance(df_adro.columns, pd.MultiIndex):
        df_adro.columns = df_adro.columns.droplevel(1)
        
    df_ihsg = yf.download("^JKSE", period="max", progress=False)
    if isinstance(df_ihsg.columns, pd.MultiIndex):
        df_ihsg.columns = df_ihsg.columns.droplevel(1)
        
    df_idr = yf.download("IDR=X", period="max", progress=False)
    if isinstance(df_idr.columns, pd.MultiIndex):
        df_idr.columns = df_idr.columns.droplevel(1)

    # 1. ADRO Technical Indicators
    df_adro['SMA_50'] = df_adro['Close'].rolling(window=50).mean()
    df_adro['SMA_200'] = df_adro['Close'].rolling(window=200).mean()
    
    # RSI (14)
    delta = df_adro['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df_adro['RSI'] = 100 - (100 / (1 + (gain / loss)))
    
    # Fast MACD (13, 21 settings)
    exp1 = df_adro['Close'].ewm(span=13, adjust=False).mean()
    exp2 = df_adro['Close'].ewm(span=21, adjust=False).mean()
    df_adro['MACD'] = exp1 - exp2
    df_adro['Signal_Line'] = df_adro['MACD'].ewm(span=9, adjust=False).mean()
    df_adro['MACD_Hist'] = df_adro['MACD'] - df_adro['Signal_Line']
    
    # 2. USD/IDR FX Indicator
    df_idr['SMA_50'] = df_idr['Close'].rolling(window=50).mean()
    
    # 3. Relative Strength (20-Day Return vs IHSG)
    adro_20d = (df_adro['Close'].iloc[-1] - df_adro['Close'].iloc[-20]) / df_adro['Close'].iloc[-20] * 100
    ihsg_20d = (df_ihsg['Close'].iloc[-1] - df_ihsg['Close'].iloc[-20]) / df_ihsg['Close'].iloc[-20] * 100

    return df_adro.dropna(), df_idr.dropna(), adro_20d, ihsg_20d

try:
    df, df_idr, adro_20d, ihsg_20d = fetch_custom_data()
except Exception as e:
    st.error("Failed to fetch live macro data. Yahoo Finance might be rate-limiting.")
    st.stop()

current_price = float(df['Close'].iloc[-1])
current_rsi = float(df['RSI'].iloc[-1])
current_macd = float(df['MACD'].iloc[-1])
current_signal = float(df['Signal_Line'].iloc[-1])
current_idr = float(df_idr['Close'].iloc[-1])
idr_sma50 = float(df_idr['SMA_50'].iloc[-1])

# --- 2. EVALUATING THE 6 QUANTITATIVE INDICATORS ---
buy_count = 0
sell_count = 0
neutral_count = 0
indicators = []

def add_indicator(metric, value, signal, explanation):
    indicators.append({
        "Metric": metric, 
        "Current Value": value, 
        "Signal": signal, 
        "How to Read": explanation
    })

# Ind 1: Price vs 200 SMA
if current_price > df['SMA_200'].iloc[-1]:
    buy_count += 1
    add_indicator("Long-Term Trend (200 SMA)", "Price Above 200 SMA", "🟢 Buy", "Price > 200 SMA signals a structural energy bull cycle and multi-month accumulation.")
else:
    sell_count += 1
    add_indicator("Long-Term Trend (200 SMA)", "Price Below 200 SMA", "🔴 Sell", "Price < 200 SMA signals a macro commodity contraction cycle and distribution.")

# Ind 2: Price vs 50 SMA
if current_price > df['SMA_50'].iloc[-1]:
    buy_count += 1
    add_indicator("Medium-Term Trend (50 SMA)", "Price Above 50 SMA", "🟢 Buy", "Price > 50 SMA shows strong quarterly energy momentum and buying interest.")
else:
    sell_count += 1
    add_indicator("Medium-Term Trend (50 SMA)", "Price Below 50 SMA", "🔴 Sell", "Price < 50 SMA shows quarterly trend deceleration and loss of buying pressure.")

# Ind 3: RSI (14)
if current_rsi < 40:
    buy_count += 1
    add_indicator("Momentum Oscillator (RSI)", f"RSI at {current_rsi:.1f}", "🟢 Buy (Oversold)", "RSI < 40 indicates heavily oversold conditions, marking a historical value accumulation zone.")
elif current_rsi > 70:
    sell_count += 1
    add_indicator("Momentum Oscillator (RSI)", f"RSI at {current_rsi:.1f}", "🔴 Sell (Overbought)", "RSI > 70 indicates overextended short-term buying, prone to sharp cyclical pullbacks.")
else:
    neutral_count += 1
    add_indicator("Momentum Oscillator (RSI)", f"RSI at {current_rsi:.1f}", "⚪ Neutral", "RSI between 40-70 signals balanced momentum without cyclical exhaustion.")

# Ind 4: Fast MACD (13, 21)
if current_macd > current_signal:
    buy_count += 1
    add_indicator("Trend Velocity (MACD 13,21)", "MACD > Signal", "🟢 Buy", "MACD line above Signal line confirms bullish short-term momentum acceleration.")
else:
    sell_count += 1
    add_indicator("Trend Velocity (MACD 13,21)", "MACD < Signal", "🔴 Sell", "MACD line below Signal line confirms short-term trend exhaustion and downside momentum.")

# Ind 5: CUSTOM MACRO - Currency Tailwind (USD/IDR vs 50 SMA)
if current_idr > idr_sma50:
    buy_count += 1
    add_indicator("Currency Tailwind (USD/IDR > 50 SMA)", f"Rp {current_idr:,.0f}", "🟢 Buy (Margin Expansion)", "A weakening Rupiah increases IDR-denominated net margins for ADRO since coal sales revenue is USD-denominated.")
else:
    sell_count += 1
    add_indicator("Currency Tailwind (USD/IDR < 50 SMA)", f"Rp {current_idr:,.0f}", "🔴 Sell (Margin Compression)", "A strengthening Rupiah compresses export margins for domestic energy producers.")

# Ind 6: CUSTOM MACRO - Sector Rotation (ADRO vs IHSG 20d)
if adro_20d > ihsg_20d:
    buy_count += 1
    add_indicator("Sector Rotation (vs IHSG 20d)", f"ADRO ({adro_20d:.1f}%) > IHSG ({ihsg_20d:.1f}%)", "🟢 Buy (Capital Inflow)", "Energy outperforming the broader benchmark signals active institutional sector rotation into commodities.")
else:
    sell_count += 1
    add_indicator("Sector Rotation (vs IHSG 20d)", f"ADRO ({adro_20d:.1f}%) < IHSG ({ihsg_20d:.1f}%)", "🔴 Sell (Capital Outflow)", "Underperforming the index indicates institutional capital rotating out of energy and into defensives/banks.")

# --- 3. DASHBOARD UI LAYOUT & CHARTS ---
col1, col2 = st.columns([2.5, 1])

# High-Visibility Plotly Range Selector
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
        fig_price.add_trace(go.Scatter(x=df.index, y=df['Close'], name='ADRO Price', line=dict(color='#2ECC71', width=2)))
        fig_price.add_trace(go.Scatter(x=df.index, y=df['SMA_200'], name='200 SMA', line=dict(color='white', width=1, dash='dash')))
        fig_price.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], name='50 SMA', line=dict(color='#E5A937', width=1)))
        
        fig_price.update_xaxes(rangeselector=timeframe_selector, type="date")
        fig_price.update_layout(template="plotly_dark", height=420, margin=dict(l=0, r=0, t=50, b=0), plot_bgcolor='#0E1117', paper_bgcolor='#0E1117')
        st.plotly_chart(fig_price, use_container_width=True)
        
    with tab2:
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI (14)', line=dict(color='#9B59B6', width=2)))
        fig_rsi.add_hline(y=70, line_dash="dash", line_color="red")
        fig_rsi.add_hline(y=30, line_dash="dash", line_color="green")
        
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
    st.metric("ADRO Price", f"Rp {current_price:,.0f}")
    st.metric("USD/IDR Exchange", f"Rp {current_idr:,.0f}")
    
    ihsg_color = "normal" if adro_20d > ihsg_20d else "inverse"
    st.metric("20D Rel. Leadership", f"{adro_20d:.1f}%", delta=f"{adro_20d - ihsg_20d:.1f}% vs IHSG", delta_color=ihsg_color)

# --- 4. ALGORITHMIC RECOMMENDATION ---
st.divider()

st.subheader(f"Algorithmic Recommendation ({buy_count} Buy / {sell_count} Sell / {neutral_count} Neutral)")

if buy_count >= 4:
    st.success(f"🟢 **MACRO BUY ZONE:** Clear majority alignment ({buy_count}/6 Buy Signals).")
elif sell_count >= 4:
    st.error(f"🔴 **MACRO SELL ZONE:** Clear majority alignment ({sell_count}/6 Sell Signals).")
else:
    st.info(f"⚪ **MIXED / NEUTRAL REGIME:** Conflicting signals ({buy_count} Buy / {sell_count} Sell / {neutral_count} Neutral). Wait for a clear majority breakout.")

with st.expander("📊 View Detailed Indicator Breakdown & How to Read", expanded=True):
    st.table(pd.DataFrame(indicators))

st.write("")

# Support / Donate Banner
st.markdown("""
<div style='background-color: #1E2127; padding: 20px; border-radius: 10px; border: 1px solid #333; text-align: center;'>
    <p style='color: #AAA; font-size: 14px; margin-bottom: 10px;'>💡 <i>YS Investment Research is provided free as an open quantitative project. If this model helps your portfolio, consider supporting the data feeds:</i></p>
    <a href="https://trakteer.id/yourname" target="_blank" style='background-color: #E5A937; color: #000; text-decoration: none; padding: 8px 16px; border-radius: 5px; font-weight: bold; font-size: 14px;'>☕ Support / Donate</a>
</div>
""", unsafe_allow_html=True)
