import streamlit as st

# --- PAGE DEFINITIONS ---

# 🟢 Public / Free Tier Pages
home_page = st.Page("pages/home.py", title="Command Center", icon="🏠", default=True)
allocator_page = st.Page("pages/portofolio_allocator.py", title="Portfolio Allocator", icon="⚖️")
bbca_page = st.Page("pages/bbca_matrix.py", title="BBCA (Public Test)", icon="🏦")

# 🔴 Premium / Gated Pages 
btc_page = st.Page("pages/btc_macro.py", title="Bitcoin (High Beta)", icon="📈")
gold_page = st.Page("pages/gold_macro.py", title="Gold (Safe Haven)", icon="🪙")
adro_page = st.Page("pages/adro_matrix.py", title="ADRO (Cyclical)", icon="⛏️")

# --- NAVIGATION ROUTER ---
pg = st.navigation({
    "Public Access": [home_page, allocator_page, bbca_page],
    "Premium Analytics": [btc_page, gold_page, adro_page]
})

# Run the app
pg.run()
