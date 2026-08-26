# ⚡ YS Investment Research Terminal

An institutional-grade quantitative research terminal and macro tracking engine designed for multi-asset market evaluation. Built on Python and Streamlit, this terminal evaluates domestic equities, commodities, and high-beta digital assets using a **100-Point Hierarchical Conviction Matrix**.

## 🌐 Application Architecture
The platform operates as a dual-layer engine:
1. **Frontend Dashboard (Streamlit Cloud):** Interactive web application providing real-time conviction scoring, dynamic chart visualizations, risk-adjusted portfolio allocation, and historical backtesting.
2. **Backend Automated Alerts (GitHub Actions):** Passively scheduled engine that crunches daily market data and broadcasts immediate regime change alerts directly to Telegram.

## 🚀 Core Features
* **🏠 Command Center:** High-level dashboard aggregating conviction scores, live pricing, and macro regimes across all tracked assets in a unified table.
* **📊 Macro Asset Matrices:** Specialized quantitative evaluation pages for:
  * **CRYPTO** (High-Beta Crypto / Global Liquidity)
  * **INDONESIAN STOCKS** (IHSG / Indonesian Stocks)
  * **GOLD** (Gold / Safe Haven & Yield Relative Risk)
* **⚖️ Portfolio Allocator:** Interactive capital allocation tool with modular asset selection controls and dynamic weight re-normalization across risk profiles.
* **🔬 Historical Backtester:** Simulation engine enabling visual testing of historical regime transitions and lag measurements against price swing pivots.

## ⚙️ 100-Point Hierarchical Conviction Engine

Regimes are evaluated daily using a weighted multi-factor model:
| Factor / Indicator | Weight | Underlying Logic |
| :--- | :---: | :--- |
| **Long-Term Trend** | `30%` | Price vs. 200-Day Simple Moving Average (SMA) |
| **Macro Overlay** | `25%` | Asset-specific macro driver (`USD/IDR`, `^TNX`, `DXY`) |
| **Sector Relative Strength** | `20%` | 20-Day rolling return comparison vs. IHSG (`^JKSE`) or S&P 500 (`^GSPC`) |
| **Medium-Term Trend** | `10%` | Price vs. 50-Day Simple Moving Average (SMA) |
| **Trend Velocity** | `10%` | Fast MACD (13, 21) signal line interaction |
| **Momentum Oscillator** | `5%` | Smart RSI (14) dip-buying in verified bull regimes |

### Regime Thresholds
* 🟢 **Macro Bull Engine:** `Score ≥ 70%`
* ⚪ **Neutral / Sideways Chop:** `31% ≤ Score ≤ 69%`
* 🔴 **Severe Bear Market:** `Score ≤ 30%`

---

## ☁️ Online Deployment & Cloud Setup

This repository is optimized for zero-cost, serverless cloud hosting. No local installation or local Python environment setup is required.

### 1. Web Application (Streamlit Community Cloud)

1. Fork or push this repository to your GitHub account.
2. Log into [Streamlit Community Cloud](https://streamlit.io/cloud).
3. Click **"New App"** and connect your repository:
   * **Main file path:** `app.py`
   * **Python version:** `3.10` or higher
4. Click **Deploy**. Your research terminal will be live at `https://<your-app-name>.streamlit.app`.

### 2. Automated Alerts (GitHub Actions)

The repository includes a automated GitHub Action pipeline (`.github/workflows/alert.yml`) configured to execute market evaluation runs on schedule.

To enable automated Telegram notifications:

1. Navigate to your GitHub Repository **Settings** > **Secrets and variables** > **Actions**.
2. Click **New repository secret** and configure:
   * **`TELEGRAM_TOKEN`**: Your Telegram Bot API token from `@BotFather`.
   * **`TELEGRAM_CHAT_ID`**: Your personal Telegram Chat or Channel ID.

---
