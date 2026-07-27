import streamlit as st

# --- PAGE DEFINITIONS ---
home_page = st.Page("pages/home.py", title="Command Center", icon="🏠", default=True)
btc_page = st.Page("pages/btc_macro.py", title="BTC", icon="📊")
gold_page = st.Page("pages/gold_macro.py", title="Gold", icon="🪙")
bbca_page = st.Page("pages/bbca_matrix.py", title="BBCA", icon="🏦")
adro_page = st.Page("pages/adro_matrix.py", title="ADRO", icon="⛏️")
allocator_page = st.Page("pages/portofolio_allocator.py", title="Portfolio Allocator", icon="⚖️")

# --- NAVIGATION ROUTER ---
pg = st.navigation([home_page, btc_page, gold_page, bbca_page, adro_page, allocator_page])
pg.run()
