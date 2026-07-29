import streamlit as st

# --- PAGE DEFINITIONS ---

# 🟢 Public / Free Tier Pages
home_page = st.Page("pages/home.py", title="Command Center", icon="🏠", default=True)
allocator_page = st.Page("pages/portofolio_allocator.py", title="Portfolio Allocator", icon="⚖️")
bbca_page = st.Page("pages/bbca_matrix.py", title="BBCA (Free)", icon="🏦")

# 🔴 Premium / Gated Pages (We will lock these later, but group them visually now)
btc_page = st.Page("pages/btc_macro.py", title="Bitcoin", icon="📈")
gold_page = st.Page("pages/gold_macro.py", title="Gold", icon="🪙")
bbca_page = st.Page("pages/bbca_matrix.py", title="BBCA", icon="🏦")
adro_page = st.Page("pages/adro_matrix.py", title="ADRO", icon="⛏️")

# --- NAVIGATION ROUTER ---
# Grouping the pages creates sleek section headers in the sidebar
pg = st.navigation({
    "Public Access": [home_page, allocator_page],
    "Premium Analytics": [btc_page, gold_page, bbca_page, adro_page]
})

# Run the app
pg.run()
