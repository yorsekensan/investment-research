import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Historical Backtest", layout="wide")

st.title("🔬 Macro Engine Backtesting")
st.write("Run a historical simulation to visualize exactly when the 100-point matrix would have triggered regime shifts compared to actual price action.")

# --- 💡 BACKTEST & USER GUIDE ---
with st.expander("📖 Backtester User Guide & Interpretation Guide", expanded=False):
    st.markdown("""
    **1. Goal of Backtesting**
    * Test historical regime transitions against actual price trends.
    * Measure structural lag (moving average confirmation) vs. false signals (whipsaws).

    **2. Input Parameters Explained**
    * **Target Asset:** The ticker you want to evaluate (e.g., `PACK.JK`, `ADRO.JK`, `BBCA.JK`).
    * **Macro Overlay:** The macro driver mapped against the asset (`IDR=X` for FX, `^TNX` for US 10Y yields, `DX-Y.NYB` for US Dollar Index).
    * **Overlay Relationship:**
        * **Direct:** A **rising** macro indicator adds **+25%** to the score (e.g., ADRO gains from weak IDR).
        * **Inverse:** A **falling** macro indicator adds **+25%** to the score (e.g., PACK gains from strong IDR; Gold/BTC gain from weak DXY).
    * **Simulation Lookback:** Choose your testing window (`1Y`, `2Y`, `3Y`, `5Y`, or `Max`).

    **3. How to Evaluate Results**
    * **Shift History Table:** Logs the exact dates the model flipped regimes (`🟢 Bull Engine` $\ge 60\%$, `🔴 Bear Market` $< 40\%$, `⚪ Neutral` $40-59\%$).
    * **Measuring Lag:** Compare the shift date against local price swing highs/lows on the chart to measure how many days after a market reversal the signal fired.
    """)

st.divider()

# --- INPUT CONTROLS ---
col1, col2, col3, col4 = st.columns(4)
with col1:
    ticker = st.selectbox("Target Asset", ["PACK.JK", "ADRO.JK", "BBCA.JK", "BTC-USD", "GC=F"])
with col2:
    macro_ticker = st.selectbox("Macro Overlay", ["IDR=X", "^TNX", "DX-Y.NYB"])
with col3:
    macro_mode = st.selectbox("Overlay Relationship", ["inverse", "direct"], 
                              help="Inverse: Falling macro chart scores 25%. Direct: Rising macro chart scores 25%.")
with col4:
    timeframe = st.selectbox("Simulation Lookback", ["1Y", "2Y", "3Y", "5Y", "Max"], index=2)

# Map lookback string to yfinance period
tf_map = {"1Y": "1y", "2Y": "2y", "3Y": "3y", "5Y": "5y", "Max": "max"}
period_str = tf_map[timeframe]

if st.button("▶ Run Historical Simulation", type="primary"):
    with st.spinner(f"Crunching {timeframe} historical data for {ticker}..."):
        try:
            tickers = [ticker, macro_ticker, "^JKSE"]
            data = yf.download(tickers, period=period_str, progress=False)['Close']
            
            df = pd.DataFrame({'Close': data[ticker]}).dropna()
            if len(df) < 50:
                st.error("Insufficient historical data for selected timeframe.")
                st.stop()
                
            df['SMA_50'] = df['Close'].rolling(50).mean()
            df['SMA_200'] = df['Close'].rolling(200).mean()
            
            # Fast MACD (13, 21)
            exp1 = df['Close'].ewm(span=13, adjust=False).mean()
            exp2 = df['Close'].ewm(span=21, adjust=False).mean()
            df['MACD'] = exp1 - exp2
            df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            
            # RSI
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['RSI'] = 100 - (100 / (1 + gain / loss.replace(0, 1e-10)))
            
            macro_series = data[macro_ticker].dropna()
            ihsg_series = data['^JKSE'].dropna()
            
            scores, regimes = [], []
            
            # Adaptive warm-up period for shorter lookback frames
            warmup_period = min(200, len(df) // 3) if len(df) < 200 else 200
            
            for i in range(len(df)):
                if i < warmup_period:
                    scores.append(0)
                    regimes.append("Initialization")
                    continue
                    
                sub = df.iloc[:i+1]
                cur = sub.iloc[-1]
                score = 0
                
                is_bull = pd.notna(cur['SMA_200']) and cur['Close'] > cur['SMA_200'] if pd.notna(cur['SMA_200']) else (cur['Close'] > cur['SMA_50'])
                if is_bull: score += 30
                if pd.notna(cur['SMA_50']) and cur['Close'] > cur['SMA_50']: score += 10
                if pd.notna(cur['RSI']) and cur['RSI'] < 40 and is_bull: score += 5
                if pd.notna(cur['MACD']) and cur['MACD'] > cur['Signal']: score += 10
                
                # Macro Evaluation
                dt = cur.name
                if dt in macro_series.index:
                    m_sub = macro_series.loc[:dt]
                    if len(m_sub) >= 50:
                        if macro_mode == "inverse" and m_sub.iloc[-1] < m_sub.rolling(50).mean().iloc[-1]: score += 25
                        elif macro_mode == "direct" and m_sub.iloc[-1] > m_sub.rolling(50).mean().iloc[-1]: score += 25
                        
                if dt in ihsg_series.index and i >= 20:
                    a_20d = (sub['Close'].iloc[-1] - sub['Close'].iloc[-20]) / sub['Close'].iloc[-20]
                    m_sub_ihsg = ihsg_series.loc[:dt]
                    if len(m_sub_ihsg) >= 20:
                        i_20d = (m_sub_ihsg.iloc[-1] - m_sub_ihsg.iloc[-20]) / m_sub_ihsg.iloc[-20]
                        if a_20d > i_20d: score += 20
                        
                scores.append(score)
                if score >= 60: regimes.append("🟢 Bull Engine")
                elif score < 40: regimes.append("🔴 Bear Market")
                else: regimes.append("⚪ Neutral")
                
            df['Score'] = scores
            df['Regime'] = regimes
            
            # Detect exact shift dates
            df['Shift'] = df['Regime'] != df['Regime'].shift(1)
            shifts = df[(df['Shift']) & (df['Regime'] != "Initialization")]
            
            tab1, tab2 = st.tabs(["📊 Shift History Table", "📈 Price vs Regime Chart"])
            
            with tab1:
                st.subheader(f"Historical Alert Triggers for {ticker} ({timeframe})")
                st.write("These are the exact dates the bot would have fired a regime change alert.")
                
                display_df = shifts[['Close', 'Regime', 'Score']].copy()
                display_df.index = display_df.index.strftime('%Y-%m-%d')
                display_df.rename(columns={'Close': 'Price at Shift (Rp/$)'}, inplace=True)
                st.dataframe(display_df, use_container_width=True)
                
            with tab2:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name='Price', line=dict(color='#888888', width=1)))
                
                # Map regimes as colored dots on the price line
                bulls = df[df['Regime'] == "🟢 Bull Engine"]
                bears = df[df['Regime'] == "🔴 Bear Market"]
                neutrals = df[df['Regime'] == "⚪ Neutral"]
                
                fig.add_trace(go.Scatter(x=bulls.index, y=bulls['Close'], mode='markers', name='Bull Regime', marker=dict(color='#2ECC71', size=5)))
                fig.add_trace(go.Scatter(x=bears.index, y=bears['Close'], mode='markers', name='Bear Regime', marker=dict(color='#E74C3C', size=5)))
                fig.add_trace(go.Scatter(x=neutrals.index, y=neutrals['Close'], mode='markers', name='Neutral', marker=dict(color='#BDC3C7', size=3)))
                
                fig.update_layout(template="plotly_dark", height=550, title=f"{ticker} {timeframe} Macro Regime Overlay", margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig, use_container_width=True)
                
        except Exception as e:
            st.error(f"Error during simulation: {e}")
