import streamlit as st
import pandas as pd
from src.analytics import load_period_data
from src.ui import apply_custom_css, THEME
from src.pages.analysis import show_analysis
from src.pages.matrix import show_matrix
from src.pages.trends import show_trends
from src.pages.simulator import show_simulator

# 1. Global Page Config & UI Setup
st.set_page_config(page_title="Brejkni to s Martinem", layout="wide", page_icon="🃏")
apply_custom_css()

# 2. Shared Data & Constants
DATA_DIR = "data"
TIMEFRAMES = {
    "All Time": "all_time",
    "2 Years": "2_years",
    "1 Year": "1_year",
    "6 Months": "6_months",
    "3 Months": "3_months"
}

@st.cache_data(ttl=3600) # 1 hour cache
def get_cached_data(period_key):
    period_val = TIMEFRAMES[period_key]
    return load_period_data(DATA_DIR, period_val)

# 3. Sidebar Header & Global Filter
with st.sidebar:
    st.markdown("""
        <div class="links-block">
            <div class="links-title">DURESS MONO</div>
            01 Premodern Dashboard ▶<br>
            02 Duress Crew ▶<br>
            <span style="color:#8A8A8A;">&nbsp;└ ▶ <a href="https://data.duresscrew.com/" style="color:#8A8A8A;text-decoration:none;">Data Source</a></span>
        </div>
    """, unsafe_allow_html=True)
    st.divider()
    
    # Global Timeframe Selector
    period_name = st.selectbox("TIMEFRAME", list(TIMEFRAMES.keys()), index=0)
    
    st.divider()

# 4. Data Retrieval
try:
    matrix_data, records_data = get_cached_data(period_name)
    all_archetypes = matrix_data["archetypes"]
    matrix_dict = matrix_data["matrix"]
except Exception as e:
    st.error(f"Chyba při načítání dat: {e}")
    st.stop()

# 5. Routing Definitions
def run_analysis():
    show_analysis(matrix_dict, all_archetypes, records_data)

def run_matrix():
    show_matrix(matrix_dict, all_archetypes)

def run_trends():
    show_trends(DATA_DIR, TIMEFRAMES)

def run_simulator():
    show_simulator(matrix_dict, all_archetypes, records_data)

# 6. Navigation Setup
pg_analysis = st.Page(run_analysis, title="Analýza Balíku", default=True)
pg_matrix = st.Page(run_matrix, title="Interaktivní Matice")
pg_trends = st.Page(run_trends, title="Meta Trendy")
pg_simulator = st.Page(run_simulator, title="Turnajový Simulátor")

pg = st.navigation({
    "Průzkumník": [pg_analysis, pg_matrix, pg_trends],
    "Nástroje": [pg_simulator]
})

# 7. Execution
pg.run()
