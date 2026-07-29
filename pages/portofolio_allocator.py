import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
import datetime
from fpdf import FPDF
import matplotlib.pyplot as plt

st.set_page_config(page_title="Portfolio Allocator", layout="wide")

st.title("⚖️ Quantitative Portfolio Allocator")
st.caption("Dynamic risk-adjusted allocation across Equities, Commodities, and Crypto.")

# --- 1. USER INPUTS ---
col1, col2 = st.columns(2)
with col1:
    capital = st.number_input("Total Investment Capital (IDR)", min_value=1000000, value=100000000, step=1000000, format="%d")
with col2:
    risk_profile = st.selectbox("Select Risk Profile", ["Conservative", "Balanced", "Aggressive", "Macro-Volatility (High Beta)"])

# --- 2. GOLD & MULTI-ASSET ALLOCATION LOGIC ---
# Defined base allocation percentages based on macro risk models
if risk_profile == "Conservative":
    alloc = {"BBCA (Structural Equity)": 45, "Gold (Safe Haven)": 35, "ADRO (Cyclical Equity)": 10, "BTC (High Beta)": 5, "IDR Cash (Liquidity)": 5}
elif risk_profile == "Balanced":
    alloc = {"BBCA (Structural Equity)": 35, "Gold (Safe Haven)": 20, "ADRO (Cyclical Equity)": 15, "BTC (High Beta)": 20, "IDR Cash (Liquidity)": 10}
elif risk_profile == "Aggressive":
    alloc = {"BBCA (Structural Equity)": 25, "Gold (Safe Haven)": 10, "ADRO (Cyclical Equity)": 25, "BTC (High Beta)": 30, "IDR Cash (Liquidity)": 10}
else: # Macro-Volatility
    alloc = {"BBCA (Structural Equity)": 10, "Gold (Safe Haven)": 10, "ADRO (Cyclical Equity)": 25, "BTC (High Beta)": 50, "IDR Cash (Liquidity)": 5}

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

with col_chart:
    fig = px.pie(df_alloc, values="Allocation (%)", names="Asset Class", hole=0.4, 
                 color="Asset Class",
                 color_discrete_map={
                     "BBCA (Structural Equity)": "#00529b", # BCA Blue
                     "Gold (Safe Haven)": "#FFD700",        # Gold
                     "ADRO (Cyclical Equity)": "#8B4513",   # Coal Brown
                     "BTC (High Beta)": "#F7931A",          # Bitcoin Orange
                     "IDR Cash (Liquidity)": "#2E8B57"      # Cash Green
                 })
    fig.update_layout(template="plotly_dark", margin=dict(t=30, b=10, l=10, r=10))
    st.plotly_chart(fig, use_container_width=True)

with col_table:
    st.dataframe(
        df_alloc.style.format({"Allocated Capital (IDR)": "Rp {:,.0f}", "Allocation (%)": "{:.1f}%"}),
        hide_index=True,
        use_container_width=True
    )
    
    st.info("💡 **Why this allocation?**\n" + 
            ("Prioritizes wealth preservation with heavy weighting in BBCA and physical Gold." if risk_profile == "Conservative" else
             "Balances structural compounding (BBCA) with macro inflation hedges (Gold/BTC)." if risk_profile == "Balanced" else
             "Heavily weights cyclical cash flow (ADRO) and global liquidity momentum (BTC)." if risk_profile == "Aggressive" else
             "Designed to aggressively capture macro liquidity cycles with maximum beta and minimal fiat exposure."))

# --- EXPORT ENGINE ---
st.divider()
st.subheader("📥 Export Portfolio Simulation")
st.write("Download your custom allocation as a raw data file or an institutional report.")

# 1. Excel Generator 
def generate_excel(df, cap, profile):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Allocation Plan')
        workbook = writer.book
        worksheet = writer.sheets['Allocation Plan']
        
        # Formatting
        money_fmt = workbook.add_format({'num_format': 'Rp #,##0'})
        pct_fmt = workbook.add_format({'num_format': '0"%"'})
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#1F4E78', 'font_color': 'white', 'align': 'center'})
        
        worksheet.set_column('A:A', 30)
        worksheet.set_column('B:B', 15, pct_fmt)
        worksheet.set_column('C:C', 25, money_fmt)
        
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_fmt)
            
        worksheet.write(len(df) + 2, 0, f"Simulation Date: {datetime.date.today()}", workbook.add_format({'italic': True}))
        worksheet.write(len(df) + 3, 0, f"Risk Profile: {profile}", workbook.add_format({'italic': True}))
        worksheet.write(len(df) + 4, 0, f"Total Capital: Rp {cap:,.0f}", workbook.add_format({'italic': True}))
        
    return output.getvalue()

# 2. PDF Generator (With Matplotlib Chart)
def generate_pdf(df, cap, profile):
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_fill_color(31, 78, 120)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 15, "YS Investment Research - Portfolio Allocation", ln=True, align="C", fill=True)
    
    # Meta Info
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("helvetica", "I", 10)
    pdf.cell(0, 10, f"Simulation Date: {datetime.date.today()} | Profile: {profile}", ln=True, align="C")
    pdf.ln(5)
    
    # Generate Pie Chart Image (In-Memory)
    fig, ax = plt.subplots(figsize=(6, 4))
    color_map = {
        "BBCA (Structural Equity)": "#00529b",
        "Gold (Safe Haven)": "#FFD700",
        "ADRO (Cyclical Equity)": "#8B4513",
        "BTC (High Beta)": "#F7931A",
        "IDR Cash (Liquidity)": "#2E8B57"
    }
    colors = [color_map.get(asset, "#999999") for asset in df["Asset Class"]]
    ax.pie(df["Allocation (%)"], labels=df["Asset Class"], autopct='%1.1f%%', startangle=140, colors=colors, textprops=dict(color="black", fontsize=8))
    ax.axis('equal') 
    
    img_buffer = BytesIO()
    plt.savefig(img_buffer, format='png', bbox_inches='tight', dpi=300)
    img_buffer.seek(0)
    plt.close(fig) # Prevent memory leaks
    
    # Embed Chart into PDF
    pdf.image(img_buffer, x=30, y=pdf.get_y(), w=150)
    pdf.ln(95) 
    
    # Table Header
    pdf.set_font("helvetica", "B", 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(90, 10, "Asset Class", border=1, align="C", fill=True)
    pdf.cell(40, 10, "Target (%)", border=1, align="C", fill=True)
    pdf.cell(60, 10, "Allocated (IDR)", border=1, align="C", fill=True)
    pdf.ln()
    
    # Table Rows
    pdf.set_font("helvetica", "", 10)
    for index, row in df.iterrows():
        pdf.cell(90, 10, str(row["Asset Class"]), border=1)
        pdf.cell(40, 10, f"{row['Allocation (%)']}%", border=1, align="C")
        pdf.cell(60, 10, f"Rp {row['Allocated Capital (IDR)']:,.0f}", border=1, align="R")
        pdf.ln()
        
    # Footer
    pdf.ln(10)
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 10, f"Total Capital Allocated: Rp {cap:,.0f}", ln=True)
    
    return pdf.output(dest="S")

# --- UI BUTTONS ---
col_export1, col_export2 = st.columns(2)

with col_export1:
    try:
        excel_data = generate_excel(df_alloc, capital, risk_profile)
        st.download_button(label="📊 Download Excel Data (.xlsx)", data=excel_data, file_name=f"YS_Portfolio_{risk_profile}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    except Exception as e:
        st.error("Excel generation failed. Check requirements.txt.")

with col_export2:
    try:
        pdf_data = generate_pdf(df_alloc, capital, risk_profile)
        st.download_button(label="📄 Download Institutional Report (.pdf)", data=pdf_data, file_name=f"YS_Portfolio_{risk_profile}.pdf", mime="application/pdf", use_container_width=True)
    except Exception as e:
        st.error("PDF generation failed. Check requirements.txt.")
