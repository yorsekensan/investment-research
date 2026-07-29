import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="ADRO Matrix", layout="wide")

st.title("⛏️ PT Alamtri Resources (ADRO.JK) Cyclical Matrix")
st.caption("Commodity, Currency, and Trend Regime Monitoring")

# --- 1. SAFE DATA FETCHING ---
@st.cache_data(ttl=300)
def fetch_adro_data():
    try:
        # We always fetch 2 years so the 200 DMA calculates correctly
        df = yf.download("ADRO.JK", period="max", progress=False)
        fx_df = yf.download("IDR=X", period="1y", progress=False)
        
        if not df.empty and isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        if not fx_df.empty and isinstance(fx_df.columns, pd.MultiIndex):
            fx_df.columns = fx_df.columns.droplevel(1)
            
        return df, fx_df
    except Exception:
        return pd.DataFrame(), pd.DataFrame()

df, fx_df = fetch_adro_data()

if df.empty or len(df) < 200 or fx_df.empty:
    st.warning("⚠️ Market data provider (yfinance) is temporarily busy or returning incomplete data. Please refresh in a few moments.")
    st.stop()

# --- 2. CALCULATE INDICATORS ---
df["MA50"] = df["Close"].rolling(50).mean()
df["MA200"] = df["Close"].rolling(200).mean()
df["pct_vs_200ma"] = (df["Close"] / df["MA200"] - 1) * 100

delta = df["Close"].diff()
gain = delta.clip(lower=0).rolling(14).mean()
loss = (-delta.clip(upper=0)).rolling(14).mean()
rs = gain / loss
df["RSI14"] = 100 - (100 / (1 + rs))

ma20 = df["Close"].rolling(20).mean()
std20 = df["Close"].rolling(20).std()
df["Upper_BB"] = ma20 + (2 * std20)
df["Lower_BB"] = ma20 - (2 * std20)
df["BB_pctB"] = (df["Close"] - df["Lower_BB"]) / (df["Upper_BB"] - df["Lower_BB"])

fx_df["MA50"] = fx_df["Close"].rolling(50).mean()

clean_df = df.dropna()
clean_fx = fx_df.dropna()

if clean_df.empty or clean_fx.empty:
    st.warning("⚠️ Calculating technicals... Waiting for complete data history.")
    st.stop()

latest = clean_df.iloc[-1]
latest_fx = clean_fx.iloc[-1]

# --- 3. SCORING REGIME LOGIC ---
buy_count, sell_count = 0, 0

if latest["MA50"] > latest["MA200"]:
    trend_status, trend_signal = "BULLISH", "🟢 BUY"
    buy_count += 1 
else: 
    trend_status, trend_signal = "BEARISH", "🔴 SELL"
    sell_count += 1

if latest["pct_vs_200ma"] <= -15:
    pct_status, pct_signal = "DEEP DISCOUNT", "🟢 BUY"
    buy_count += 1
elif latest["pct_vs_200ma"] >= 15:
    pct_status, pct_signal = "OVEREXTENDED", "🔴 SELL"
    sell_count += 1
else:
    pct_status, pct_signal = "NEUTRAL", "⚪ HOLD"

if latest["RSI14"] <= 35:
    rsi_status, rsi_signal = "OVERSOLD", "🟢 BUY"
    buy_count += 1
elif latest["RSI14"] >= 70:
    rsi_status, rsi_signal = "OVERBOUGHT", "🔴 SELL"
    sell_count += 1
else:
    rsi_status, rsi_signal = "NEUTRAL", "⚪ HOLD"

if latest["BB_pctB"] <= 0:
    bb_status, bb_signal = "BELOW LOWER BAND", "🟢 BUY"
    buy_count += 1
elif latest["BB_pctB"] >= 1:
    bb_status, bb_signal = "ABOVE UPPER BAND", "🔴 SELL"
    sell_count += 1
else:
    bb_status, bb_signal = "WITHIN BANDS", "⚪ HOLD"

if latest_fx["Close"] > latest_fx["MA50"]:
    fx_status, fx_signal = "TAILWIND (Strong USD)", "🟢 BUY"
    buy_count += 1
else:
    fx_status, fx_signal = "HEADWIND (Weak USD)", "🔴 SELL"
    sell_count += 1

if buy_count >= 3:
    verdict = "CYCLICAL BUY ZONE"
    color = "normal"
elif sell_count >= 3:
    verdict = "CYCLICAL SELL ZONE"
    color = "inverse"
else:
    verdict = "NEUTRAL REGIME"
    color = "off"

# --- 4. DASHBOARD UI & RECOMMENDATION ---
st.divider()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Live Price", f"Rp{latest['Close']:,.0f}")
col2.metric("Trend (50 vs 200)", trend_status)
col3.metric("% vs 200 DMA", f"{latest['pct_vs_200ma']:+.2f}%")
col4.metric("RSI (14)", f"{latest['RSI14']:.1f}")
col5.metric("USD/IDR Overlay", "TAILWIND" if "TAILWIND" in fx_status else "HEADWIND")

st.divider()

st.subheader("Algorithmic Recommendation")
if verdict == "CYCLICAL BUY ZONE":
    st.success(f"**🟢 {verdict}:** ADRO is showing structural weakness in price but strong underlying macro/technical setup. Accumulate for cyclical rebound.")
elif verdict == "CYCLICAL SELL ZONE":
    st.error(f"**🔴 {verdict}:** ADRO is technically overextended. Consider trimming positions or taking profits as momentum exhausts.")
else:
    st.info(f"**⚪ {verdict}:** ADRO is chopping within normal structural bounds. Maintain current allocations and wait for a clear macro break.")

with st.expander("📊 View Detailed Indicator Breakdown", expanded=False):
    matrix_data = {
        "Indicator": ["Trend (50 vs 200 DMA)", "Deviation from 200 DMA", "RSI (14)", "Bollinger %B", "USD/IDR Macro Overlay"],
        "Current Value": [f"50DMA: Rp{latest['MA50']:,.0f}", f"{latest['pct_vs_200ma']:+.2f}%", f"{latest['RSI14']:.1f}", f"{latest['BB_pctB']:.2f}", f"Rp{latest_fx['Close']:,.0f}"],
        "Condition": [trend_status, pct_status, rsi_status, bb_status, fx_status],
        "Signal": [trend_signal, pct_signal, rsi_signal, bb_signal, fx_signal]
    }
    st.table(pd.DataFrame(matrix_data))

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

# --- 5. TIMEFRAME SELECTOR & INTERACTIVE CHARTS ---
st.subheader("Price Action & Moving Averages")

timeframe = st.radio(
    "Select Chart Timeframe:",
    ["3 Months", "6 Months", "1 Year", "2 Years", "5 Years", "Max"],
    horizontal=True,
    index=5 # Defaults to Max
)

end_date = clean_df.index.max()
if timeframe == "3 Months":
    start_date = end_date - pd.DateOffset(months=3)
elif timeframe == "6 Months":
    start_date = end_date - pd.DateOffset(months=6)
elif timeframe == "1 Year":
    start_date = end_date - pd.DateOffset(years=1)
elif timeframe == "2 Years":
    start_date = end_date - pd.DateOffset(years=2)
elif timeframe == "5 Years":
    start_date = end_date - pd.DateOffset(years=5)
else:
    start_date = clean_df.index.min()
    
plot_df = clean_df[clean_df.index >= start_date]

# 1. Main Candlestick Chart (Fixed 200 DMA Color to Bright Cyan)
fig_price = go.Figure()
fig_price.add_trace(go.Candlestick(x=plot_df.index, open=plot_df['Open'], high=plot_df['High'], low=plot_df['Low'], close=plot_df['Close'], name='Price'))
fig_price.add_trace(go.Scatter(x=plot_df.index, y=plot_df['MA50'], line=dict(color='orange', width=1.5), name='50-Day MA'))
fig_price.add_trace(go.Scatter(x=plot_df.index, y=plot_df['MA200'], line=dict(color='#00FFFF', width=2), name='200-Day MA (Cyan)')) # <-- Brightened
fig_price.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=450, margin=dict(l=10, r=10, t=30, b=10))
fig_price.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
st.plotly_chart(fig_price, use_container_width=True)

# 2. Sub-Charts Grid (3 Columns now)
col_chart1, col_chart2, col_chart3 = st.columns(3)

with col_chart1:
    st.subheader("200 DMA Deviation (%)")
    fig_dma = go.Figure()
    fig_dma.add_trace(go.Scatter(x=plot_df.index, y=plot_df['pct_vs_200ma'], line=dict(color='#00FFFF', width=1.5), name='% vs 200DMA'))
    fig_dma.add_hline(y=15, line_dash="dash", line_color="red", annotation_text="Overextended (+15%)")
    fig_dma.add_hline(y=-15, line_dash="dash", line_color="green", annotation_text="Discount (-15%)")
    fig_dma.add_hline(y=0, line_dash="dot", line_color="gray")
    fig_dma.update_layout(template="plotly_dark", height=280, margin=dict(l=10, r=10, t=30, b=10))
    fig_dma.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    st.plotly_chart(fig_dma, use_container_width=True)

with col_chart2:
    st.subheader("Relative Strength Index (RSI)")
    fig_rsi = go.Figure()
    fig_rsi.add_trace(go.Scatter(x=plot_df.index, y=plot_df['RSI14'], line=dict(color='purple', width=1.5), name='RSI (14)'))
    fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="70")
    fig_rsi.add_hline(y=35, line_dash="dash", line_color="green", annotation_text="35")
    fig_rsi.update_layout(template="plotly_dark", height=280, margin=dict(l=10, r=10, t=30, b=10))
    fig_rsi.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    st.plotly_chart(fig_rsi, use_container_width=True)

with col_chart3:
    st.subheader("Bollinger Bands")
    fig_bb = go.Figure()
    fig_bb.add_trace(go.Scatter(x=plot_df.index, y=plot_df['Upper_BB'], line=dict(color='gray', dash='dot'), name='Upper'))
    fig_bb.add_trace(go.Scatter(x=plot_df.index, y=plot_df['Lower_BB'], line=dict(color='gray', dash='dot'), fill='tonexty', fillcolor='rgba(128, 128, 128, 0.15)', name='Lower'))
    fig_bb.add_trace(go.Scatter(x=plot_df.index, y=plot_df['Close'], line=dict(color='white', width=1.2), name='Price'))
    fig_bb.update_layout(template="plotly_dark", height=280, margin=dict(l=10, r=10, t=30, b=10))
    fig_bb.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    st.plotly_chart(fig_bb, use_container_width=True)
    
# --- 6. MACRO RESEARCH EXPANDER ---
with st.expander("View Manager's Research Thesis"):
    st.markdown("""
    **The Cyclical Nature of ADRO:**
    Unlike financial assets (like BBCA) that compound steadily, ADRO trades structurally based on commodity and macro cycles. 
    *   **The 15% DMA Rule:** Coal cycles create violent swings. We look for deep -15% structural discounts from the 200-day average to initiate cyclical accumulation.
    *   **The FX Component:** ADRO generates revenue in USD but pays domestic costs in IDR. A strengthening dollar (USD/IDR > 50MA) creates an artificial margin expansion for the asset.
    """)
