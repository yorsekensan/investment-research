import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
import datetime

st.set_page_config(page_title="Portfolio Allocator", layout="wide")

st.title("⚖️ Quantitative Portfolio Allocator")
st.caption("Dynamic risk-adjusted allocation across Equities, Commodities, Crypto, and Small-Caps.")

# --- 1. USER INPUTS & ASSET SELECTION ---
col1, col2 = st.columns(2)
with col1:
    capital = st.number_input("Total Investment Capital (IDR)", min_value=1000000, value=100000000, step=1000000, format="%d")
with col2:
    risk_profile = st.selectbox("Select Baseline Risk Profile", ["Conservative", "Balanced", "Aggressive", "Macro-Volatility (High Beta)"])

st.subheader("🛠️ Asset Inclusion Control")
st.write("Uncheck any asset to exclude it from this portfolio simulation. Weights will automatically re-normalize to 100%.")

all_available_assets = [
    "BBCA (Structural Equity)",
    "Gold (Safe Haven)",
    "ADRO (Cyclical Equity)",
    "PACK (Small Cap / Rights)",
    "BTC (High Beta)",
    "IDR Cash (Liquidity)"
]

selected_assets = st.multiselect(
    "Active Assets in Portfolio",
    options=all_available_assets,
    default=["BBCA (Structural Equity)", "Gold (Safe Haven)", "ADRO (Cyclical Equity)", "PACK (Small Cap / Rights)", "BTC (High Beta)", "IDR Cash (Liquidity)"]
)

if not selected_assets:
    st.warning("Please select at least one asset to generate the allocation plan.")
    st.stop()

# --- 2. DYNAMIC WEIGHT ALLOCATION LOGIC ---
base_weights = {
    "Conservative": {
        "BBCA (Structural Equity)": 40, "Gold (Safe Haven)": 35, "ADRO (Cyclical Equity)": 10, 
        "PACK (Small Cap / Rights)": 5, "BTC (High Beta)": 5, "IDR Cash (Liquidity)": 5
    },
    "Balanced": {
        "BBCA (Structural Equity)": 30, "Gold (Safe Haven)": 20, "ADRO (Cyclical Equity)": 15, 
        "PACK (Small Cap / Rights)": 10, "BTC (High Beta)": 15, "IDR Cash (Liquidity)": 10
    },
    "Aggressive": {
        "BBCA (Structural Equity)": 20, "Gold (Safe Haven)": 10, "ADRO (Cyclical Equity)": 20, 
        "PACK (Small Cap / Rights)": 15, "BTC (High Beta)": 25, "IDR Cash (Liquidity)": 10
    },
    "Macro-Volatility (High Beta)": {
        "BBCA (Structural Equity)": 10, "Gold (Safe Haven)": 10, "ADRO (Cyclical Equity)": 20, 
        "PACK (Small Cap / Rights)": 15, "BTC (High Beta)": 40, "IDR Cash (Liquidity)": 5
    }
}

# Filter weights for selected assets only
raw_alloc = {asset: base_weights[risk_profile][asset] for asset in selected_assets}
total_weight = sum(raw_alloc.values())

# Normalize weights to exactly 100%
alloc = {asset: (weight / total_weight) * 100 for asset, weight in raw_alloc.items()}

# Calculate exact fiat amounts
data = []
for asset, pct in alloc.items():
    amount = capital * (pct / 100)
    data.append({"Asset Class": asset, "Allocation (%)": pct, "Allocated Capital (IDR)": amount})

df_alloc = pd.DataFrame(data)

# --- 3. VISUALIZATION ---
st.divider()
st.subheader(f"Recommended {risk_profile} Portfolio")

col_chart, col_table = st.columns([1.5, 1])

color_mapping = {
    "BBCA (Structural Equity)": "#00529b", # BCA Blue
    "Gold (Safe Haven)": "#FFD700",        # Gold
    "ADRO (Cyclical Equity)": "#8B4513",   # Coal Brown
    "PACK (Small Cap / Rights)": "#8E44AD",# Purple
    "BTC (High Beta)": "#F7931A",          # Bitcoin Orange
    "IDR Cash (Liquidity)": "#2E8B57"      # Cash Green
}

with col_chart:
    fig = px.pie(df_alloc, values="Allocation (%)", names="Asset Class", hole=0.4, 
                 color="Asset Class",
                 color_discrete_map=color_mapping)
    fig.update_layout(template="plotly_dark", margin=dict(t=30, b=10, l=10, r=10))
    st.plotly_chart(fig, use_container_width=True)

with col_table:
    st.dataframe(
        df_alloc.style.format({"Allocated Capital (IDR)": "Rp {:,.0f}", "Allocation (%)": "{:.1f}%"}),
        hide_index=True,
        use_container_width=True
    )
    
    st.info("💡 **Portfolio Structure:** Weights are dynamically re-normalized based on your active asset selections to maintain risk parity.")

# --- EXPORT ENGINE ---
st.divider()
st.subheader("📥 Export Portfolio Simulation")
st.write("Download your raw data spreadsheet for local analysis.")

def generate_excel(df, cap, profile):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Allocation Plan')
        workbook = writer.book
        worksheet = writer.sheets['Allocation Plan']
        
        money_fmt = workbook.add_format({'num_format': 'Rp #,##0'})
        pct_fmt = workbook.add_format({'num_format': '0.0"%"'})
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#1F4E78', 'font_color': 'white', 'align': 'center'})
        
        worksheet.set_column('A:A', 35)
        worksheet.set_column('B:B', 15, pct_fmt)
        worksheet.set_column('C:C', 25, money_fmt)
        
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_fmt)
            
        worksheet.write(len(df) + 2, 0, f"Simulation Date: {datetime.date.today()}", workbook.add_format({'italic': True}))
        worksheet.write(len(df) + 3, 0, f"Risk Profile: {profile}", workbook.add_format({'italic': True}))
        worksheet.write(len(df) + 4, 0, f"Total Capital: Rp {cap:,.0f}", workbook.add_format({'italic': True}))
        
    return output.getvalue()

try:
    excel_data = generate_excel(df_alloc, capital, risk_profile)
    st.download_button(
        label="📊 Download Excel Data (.xlsx)",
        data=excel_data,
        file_name=f"YS_Portfolio_{risk_profile}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
except Exception as e:
    st.error("Excel generation encountered an issue.")
