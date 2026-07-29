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
DESCRIPTION = "Custom macro-tracking for coal exports. Includes USD/IDR currency tailwinds and IHSG relative strength."

st.set_page_config(page_title=f"{PAGE_TITLE} Matrix", page_icon=PAGE_ICON, layout="wide")

st.title(f"{PAGE_ICON} {PAGE_TITLE} Macro Matrix")
st.write(DESCRIPTION)
st.divider()

# --- 1. DATA FETCHING (ADRO, USD/IDR, IHSG) ---
@st.cache_data(ttl=3600)
def fetch_custom_data():
    # Fetch ADRO
    df_adro = yf.download(TICKER, period="1y", progress=False)
    if isinstance(df_adro.columns, pd.MultiIndex):
        df_adro.columns = df_adro.columns.droplevel(1)
        
    # Fetch USD/IDR Forex
    df_idr = yf.download("IDR=X", period="1y", progress=False)
    if isinstance(df_idr.columns, pd.MultiIndex):
        df_idr.columns = df_idr.columns.droplevel(1)
        
    # Fetch IHSG (Jakarta Composite)
    df_ihsg = yf.download("^JKSE", period="1y", progress=False)
    if isinstance(df_ihsg.columns, pd.MultiIndex):
        df_ihsg.columns = df_ihsg.columns.droplevel(1)

    # 1. ADRO Indicators
    df_adro['SMA_50'] = df_adro['Close'].rolling(window=50).mean()
    df_adro['SMA_200'] = df_adro['Close'].rolling(window=200).mean()
    
    delta = df_adro['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df_adro['RSI'] = 100 - (100 / (1 + (gain / loss)))
    
    exp1 = df_adro['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df_adro['Close'].ewm(span=26, adjust=False).mean()
    df_adro['MACD'] = exp1 - exp2
    df_adro['Signal_Line'] = df_adro['MACD'].ewm(span=9, adjust=False).mean()
    df_adro['MACD_Hist'] = df_adro['MACD'] - df_adro['Signal_Line']
    
    # 2. USD/IDR Indicators
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
current_usdidr = float(df_idr['Close'].iloc[-1])
idr_sma50 = float(df_idr['SMA_50'].iloc[-1])

# --- 2. EVALUATING THE 6 ADRO-SPECIFIC INDICATORS ---
buy_count = 0
sell_count = 0
neutral_count = 0
indicators = []

# Ind 1: Price vs 200 SMA
if current_price > df['SMA_200'].iloc[-1]:
    buy_count += 1
    indicators.append({"Metric": "Long-Term Trend (Price vs 200 SMA)", "Current Value": "Price Above 200 SMA", "Signal": "🟢 Buy"})
else:
    sell_count += 1
    indicators.append({"Metric": "Long-Term Trend (Price vs 200 SMA)", "Current Value": "Price Below 200 SMA", "Signal": "🔴 Sell"})

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

# Ind 4: MACD
if current_macd > current_signal:
    buy_count += 1
    indicators.append({"Metric": "Trend Momentum (MACD)", "Current Value": "MACD > Signal Line", "Signal": "🟢 Buy"})
else:
    sell_count += 1
    indicators.append({"Metric": "Trend Momentum (MACD)", "Current Value": "MACD < Signal Line", "Signal": "🔴 Sell"})

# Ind 5: CUSTOM MACRO - USD/IDR Tailwind
if current_usdidr > idr_sma50:
    buy_count += 1
    indicators.append({"Metric": "Currency Tailwind (USD/IDR > 50 SMA)", "Current Value": f"Rp {current_usdidr:,.0f} (Weak IDR)", "Signal": "🟢 Buy (Margin Expansion)"})
else:
    sell_count += 1
    indicators.append({"Metric": "Currency Tailwind (USD/IDR < 50 SMA)", "Current Value": f"Rp {current_usdidr:,.0f} (Strong IDR)", "Signal": "🔴 Sell (Margin Contraction)"})

# Ind 6: CUSTOM MACRO - Sector Rotation vs IHSG
if adro_20d > ihsg_20d:
    buy_count += 1
    indicators.append({"Metric": "Relative Strength (ADRO vs IHSG 20d)", "Current Value": f"ADRO ({adro_20d:.1f}%) > IHSG ({ihsg_20d:.1f}%)", "Signal": "🟢 Buy (Capital Inflow)"})
else:
    sell_count += 1
    indicators.append({"Metric": "Relative Strength (ADRO vs IHSG 20d)", "Current Value": f"ADRO ({adro_20d:.1f}%) < IHSG ({ihsg_20d:.1f}%)", "Signal": "🔴 Sell (Capital Outflow)"})

# --- 3. DASHBOARD UI LAYOUT & CHARTS ---
col1, col2 = st.columns([2.5, 1])

with col1:
    tab1, tab2, tab3 = st.tabs(["📈 Price & SMAs", "⚡ RSI Oscillator", "📊 MACD Histogram"])
    
    with tab1:
        fig_price = go.Figure()
        fig_price.add_trace(go.Scatter(x=df.index, y=df['Close'], name='ADRO Price', line=dict(color='#E5A937', width=2)))
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
        fig_macd.add_trace(go.Scatter(x=df.index, y=df['MACD'], name='MACD', line=dict(color='#3498DB', width=1.5)))
        fig_macd.add_trace(go.Scatter(x=df.index, y=df['Signal_Line'], name='Signal', line=dict(color='#E67E22', width=1.5)))
        colors = ['#2ECC71' if val >= 0 else '#E74C3C' for val in df['MACD_Hist']]
        fig_macd.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], name='Histogram', marker_color=colors))
        fig_macd.update_layout(template="plotly_dark", height=350, margin=dict(l=0, r=0, t=20, b=0), plot_bgcolor='#0E1117', paper_bgcolor='#0E1117')
        st.plotly_chart(fig_macd, use_container_width=True)

with col2:
    st.subheader("Live Metrics")
    st.metric("ADRO Price", f"Rp {current_price:,.0f}")
    st.metric("USD/IDR Rate", f"Rp {current_usdidr:,.0f}")
    
    ihsg_color = "normal" if adro_20d > ihsg_20d else "inverse"
    st.metric("20D Rel. Strength", f"{adro_20d:.1f}%", delta=f"{adro_20d - ihsg_20d:.1f}% vs IHSG", delta_color=ihsg_color)

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
