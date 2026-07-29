import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

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
st.divider()

# --- 1. DATA FETCHING (Gold, DXY, US10Y) ---
@st.cache_data(ttl=3600)
def fetch_custom_data():
    # Fetch Gold Futures
    df_gold = yf.download(TICKER, period="1y", progress=False)
    if isinstance(df_gold.columns, pd.MultiIndex):
        df_gold.columns = df_gold.columns.droplevel(1)
        
    # Fetch DXY (US Dollar Index)
    df_dxy = yf.download("DX-Y.NYB", period="1y", progress=False)
    if isinstance(df_dxy.columns, pd.MultiIndex):
        df_dxy.columns = df_dxy.columns.droplevel(1)
        
    # Fetch US 10-Year Treasury Yield (^TNX)
    df_tnx = yf.download("^TNX", period="1y", progress=False)
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
    
    # MACD (Custom 13, 21 settings)
    exp1 = df_gold['Close'].ewm(span=13, adjust=False).mean() # Fast EMA 13
    exp2 = df_gold['Close'].ewm(span=21, adjust=False).mean() # Slow EMA 21
    df_gold['MACD'] = exp1 - exp2
    df_gold['Signal_Line'] = df_gold['MACD'].ewm(span=9, adjust=False).mean() # Standard 9-period Signal Line
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

# --- 2. EVALUATING THE 6 QUANTITATIVE INDICATORS ---
buy_count = 0
sell_count = 0
neutral_count = 0
indicators = []

# Ind 1: Price vs 200 SMA
if current_price > df['SMA_200'].iloc[-1]:
    buy_count += 1
    indicators.append({"Metric": "Long-Term Structural Regime (Price vs 200 SMA)", "Current Value": "Price Above 200 SMA", "Signal": "🟢 Buy"})
else:
    sell_count += 1
    indicators.append({"Metric": "Long-Term Structural Regime (Price vs 200 SMA)", "Current Value": "Price Below 200 SMA", "Signal": "🔴 Sell"})

# Ind 2: Price vs 50 SMA
if current_price > df['SMA_50'].iloc[-1]:
    buy_count += 1
    indicators.append({"Metric": "Medium-Term Trend (Price vs 50 SMA)", "Current Value": "Price Above 50 SMA", "Signal": "🟢 Buy"})
else:
    sell_count += 1
    indicators.append({"Metric": "Medium-Term Trend (Price vs 50 SMA)", "Current Value": "Price Below 50 SMA", "Signal": "🔴 Sell"})

# Ind 3: RSI (14)
if current_rsi < 40:
    buy_count += 1
    indicators.append({"Metric": "Momentum Oscillator (RSI 14)", "Current Value": f"RSI at {current_rsi:.1f} (Oversold)", "Signal": "🟢 Buy"})
elif current_rsi > 70:
    sell_count += 1
    indicators.append({"Metric": "Momentum Oscillator (RSI 14)", "Current Value": f"RSI at {current_rsi:.1f} (Overbought)", "Signal": "🔴 Sell"})
else:
    neutral_count += 1
    indicators.append({"Metric": "Momentum Oscillator (RSI 14)", "Current Value": f"RSI at {current_rsi:.1f}", "Signal": "⚪ Neutral"})

# Ind 4: Custom Fast MACD (13, 21)
if current_macd > current_signal:
    buy_count += 1
    indicators.append({"Metric": "Trend Momentum (MACD 13,21)", "Current Value": "MACD > Signal Line", "Signal": "🟢 Buy"})
else:
    sell_count += 1
    indicators.append({"Metric": "Trend Momentum (MACD 13,21)", "Current Value": "MACD < Signal Line", "Signal": "🔴 Sell"})

# Ind 5: CUSTOM MACRO - Global USD Debasement (DXY vs 50 SMA)
if current_dxy < dxy_sma50:
    buy_count += 1
    indicators.append({"Metric": "USD Debasement Tailwind (DXY < 50 SMA)", "Current Value": f"DXY at {current_dxy:.2f} (Weak USD)", "Signal": "🟢 Buy (Purchasing Power Boost)"})
else:
    sell_count += 1
    indicators.append({"Metric": "USD Debasement Tailwind (DXY > 50 SMA)", "Current Value": f"DXY at {current_dxy:.2f} (Strong USD)", "Signal": "🔴 Sell (USD Strength Headwind)"})

# Ind 6: CUSTOM MACRO - Opportunity Cost (US 10Y Yield vs 50 SMA)
if current_tnx < tnx_sma50:
    buy_count += 1
    indicators.append({"Metric": "Opportunity Cost (US 10Y < 50 SMA)", "Current Value": f"Yield at {current_tnx:.2f}% (Easing Yields)", "Signal": "🟢 Buy (Lower Opportunity Cost)"})
else:
    sell_count += 1
    indicators.append({"Metric": "Opportunity Cost (US 10Y > 50 SMA)", "Current Value": f"Yield at {current_tnx:.2f}% (Rising Yields)", "Signal": "🔴 Sell (Higher Bond Competition)"})

# --- 3. DASHBOARD UI LAYOUT & CHARTS ---
col1, col2 = st.columns([2.5, 1])

with col1:
    tab1, tab2, tab3 = st.tabs(["📈 Price & SMAs", "⚡ RSI Oscillator", "📊 MACD (13,21) Histogram"])
    
    with tab1:
        fig_price = go.Figure()
        fig_price.add_trace(go.Scatter(x=df.index, y=df['Close'], name='Gold Price', line=dict(color='#E5A937', width=2)))
        fig_price.add_trace(go.Scatter(x=df.index, y=df['SMA_200'], name='200 SMA', line=dict(color='white', width=1, dash='dash')))
        fig_price.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], name='50 SMA', line=dict(color='#00529b', width=1)))
        fig_price.update_layout(template="plotly_dark", height=350, margin=dict(l=0, r=0, t=20, b=0), plot_bgcolor='#0E1117', paper_bgcolor='#0E1117')
        st.plotly_chart(fig_price, use_container_width=True)
        
    with tab2:
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI (14)', line=dict(color='#9B59B6', width=2)))
        fig_rsi.add_hline(y=70, line_dash="dash", line_color="red")
        fig_rsi.add_hline(y=30, line_dash="dash", line_color="green")
        fig_rsi.update_layout(template="plotly_dark", height=350, margin=dict(l=0, r=0, t=20, b=0), plot_bgcolor='#0E1117', paper_bgcolor='#0E1117')
        st.plotly_chart(fig_rsi, use_container_width=True)

    with tab3:
        fig_macd = go.Figure()
        fig_macd.add_trace(go.Scatter(x=df.index, y=df['MACD'], name='MACD (13,21)', line=dict(color='#3498DB', width=1.5)))
        fig_macd.add_trace(go.Scatter(x=df.index, y=df['Signal_Line'], name='Signal', line=dict(color='#E67E22', width=1.5)))
        colors = ['#2ECC71' if val >= 0 else '#E74C3C' for val in df['MACD_Hist']]
        fig_macd.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], name='Histogram', marker_color=colors))
        fig_macd.update_layout(template="plotly_dark", height=350, margin=dict(l=0, r=0, t=20, b=0), plot_bgcolor='#0E1117', paper_bgcolor='#0E1117')
        st.plotly_chart(fig_macd, use_container_width=True)

with col2:
    st.subheader("Live Metrics")
    st.metric("Gold Price (/oz)", f"${current_price:,.2f}")
    st.metric("DXY Dollar Index", f"{current_dxy:.2f}")
    st.metric("US 10Y Yield", f"{current_tnx:.2f}%")

# --- 4. ALGORITHMIC RECOMMENDATION ---
st.divider()

st.subheader(f"Algorithmic Recommendation ({buy_count} Buy / {sell_count} Sell / {neutral_count} Neutral)")

if buy_count >= 4:
    st.success(f"🟢 **MACRO BUY ZONE:** Clear majority alignment ({buy_count}/6 Buy Signals).")
elif sell_count >= 4:
    st.error(f"🔴 **MACRO SELL ZONE:** Clear majority alignment ({sell_count}/6 Sell Signals).")
else:
    st.info(f"⚪ **MIXED / NEUTRAL REGIME:** Conflicting signals ({buy_count} Buy / {sell_count} Sell / {neutral_count} Neutral). Wait for a clear majority breakout.")

with st.expander("📊 View Detailed Indicator Breakdown", expanded=True):
    st.table(pd.DataFrame(indicators))

st.write("")

# Support / Donate Banner
st.markdown("""
<div style='background-color: #1E2127; padding: 20px; border-radius: 10px; border: 1px solid #333; text-align: center;'>
    <p style='color: #AAA; font-size: 14px; margin-bottom: 10px;'>💡 <i>YS Investment Research is provided free as an open quantitative project. If this model helps your portfolio, consider supporting the data feeds:</i></p>
    <a href="https://trakteer.id/yourname" target="_blank" style='background-color: #E5A937; color: #000; text-decoration: none; padding: 8px 16px; border-radius: 5px; font-weight: bold; font-size: 14px;'>☕ Support / Donate</a>
</div>
""", unsafe_allow_html=True)
