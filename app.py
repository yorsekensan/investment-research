import streamlit as st

# --- PAGE DEFINITIONS ---
home_page = st.Page("pages/home.py", title="Command Center", icon="🏠", default=True)
allocator_page = st.Page("pages/portofolio_allocator.py", title="Portfolio Allocator", icon="⚖️")
backtest_page = st.Page("pages/backtest.py", title="Historical Backtest", icon="🔬")
bbca_page = st.Page("pages/bbca_matrix.py", title="BBCA (Equities)", icon="🏦")
btc_page = st.Page("pages/btc_macro.py", title="Bitcoin (High Beta)", icon="📈")
gold_page = st.Page("pages/gold_macro.py", title="Gold (Safe Haven)", icon="🪙")
adro_page = st.Page("pages/adro_matrix.py", title="ADRO (Cyclical)", icon="⛏️")
pack_page = st.Page("pages/pack_matrix.py", title="PACK (Commodity)", icon="📦")
foru_page = st.Page("pages/foru_matrix.py", title="FORU (Media/Corp Action)", icon="📰")
dooh_page = st.Page("pages/dooh_matrix.py", title="DOOH (OOH Media)", icon=" billboards")

# --- UNIFIED NAVIGATION ---
pg = st.navigation({
    "Research Terminal": [home_page, allocator_page, backtest_page],
    "Asset Matrices": [bbca_page, btc_page, gold_page, adro_page, pack_page, foru_page, dooh_page]
})

pg.run()
