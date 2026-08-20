import streamlit as st

# --- PAGE DEFINITIONS ---
home_page = st.Page("pages/home.py", title="Command Center", icon="🏠", default=True)
allocator_page = st.Page("pages/portofolio_allocator.py", title="Portfolio Allocator", icon="⚖️")
bbca_page = st.Page("pages/bbca_matrix.py", title="BBCA (Equities)", icon="🏦")
btc_page = st.Page("pages/btc_macro.py", title="Bitcoin (High Beta)", icon="📈")
gold_page = st.Page("pages/gold_macro.py", title="Gold (Safe Haven)", icon="🪙")
adro_page = st.Page("pages/adro_matrix.py", title="ADRO (Cyclical)", icon="⛏️")
pack_page = st.Page("pages/pack_matrix.py", title="PACK (Small Cap)", icon="📦⛏️")

# --- UNIFIED NAVIGATION ---
pg = st.navigation({
    "Research Terminal": [home_page, allocator_page],
    "Asset Matrices": [bbca_page, btc_page, gold_page, adro_page, pack_page] # Added PACK to menu
})

pg.run()
