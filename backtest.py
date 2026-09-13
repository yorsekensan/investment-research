import yfinance as yf
import pandas as pd

def backtest_regime(ticker, macro_ticker, macro_mode):
    # Fetch historical daily data
    tickers = [ticker, macro_ticker, "^JKSE"]
    data = yf.download(tickers, period="3y", progress=False)['Close']
    
    df = pd.DataFrame({'Close': data[ticker]}).dropna()
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
    
    for i in range(len(df)):
        if i < 200:
            scores.append(0)
            regimes.append("Initialization")
            continue
            
        sub = df.iloc[:i+1]
        cur = sub.iloc[-1]
        score = 0
        
        is_bull = pd.notna(cur['SMA_200']) and cur['Close'] > cur['SMA_200']
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
    
    # Detect regime transitions
    df['Shift'] = df['Regime'] != df['Regime'].shift(1)
    shifts = df[(df['Shift']) & (df['Regime'] != "Initialization")]
    
    print(f"\n=== BACKTEST REGIME SHIFTS FOR {ticker} ===")
    for idx, row in shifts.iterrows():
        print(f"Date: {idx.strftime('%Y-%m-%d')} | Price: Rp {row['Close']:,.0f} | Shifted To: {row['Regime']} (Score: {row['Score']}%)")

if __name__ == "__main__":
    backtest_regime("PACK.JK", "IDR=X", "inverse")
