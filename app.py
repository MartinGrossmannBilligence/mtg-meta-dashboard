import streamlit as st
import pandas as pd
from src.analytics import load_period_data, calculate_expected_winrate
from src.ui import apply_custom_css, THEME
from src.pages.analysis import show_analysis
from src.pages.meta_overview import show_meta_overview
from src.pages.simulator import show_simulator

# ── 1. Page Config ────────────────────────────────────────────────────────────
st.set_page_config(page_title="Premodern Meta Lab", layout="wide")
apply_custom_css()

# ── 2. Constants ──────────────────────────────────────────────────────────────
DATA_DIR = "data"
TIMEFRAMES = {
    "All Time": "all_time",
    "2 Years":  "2_years",
    "1 Year":   "1_year",
    "6 Months": "6_months",
}

@st.cache_data(ttl=3600)
def get_cached_data(period_key):
    return load_period_data(DATA_DIR, TIMEFRAMES[period_key])

# "Premodern Meta Lab" title is injected above the nav links via CSS ::before
# in apply_custom_css().
# We inject the subtitle as a raw HTML block positioned absolutely.
with st.sidebar:
    st.markdown(
        '<div class="sidebar-subtitle">'
        'Based on <a href="https://data.duresscrew.com/" target="_blank">Duress Crew</a> data'
        '</div>',
        unsafe_allow_html=True,
    )
    period_name = st.selectbox("TIMEFRAME", list(TIMEFRAMES.keys()), index=0)
    st.divider()

# ── 4. Data ───────────────────────────────────────────────────────────────────
try:
    matrix_data, records_data = get_cached_data(period_name)
    all_archetypes = matrix_data["archetypes"]
    matrix_dict    = matrix_data["matrix"]
except Exception as e:
    st.error(f"Failed to load data: {e}")
    st.stop()

# ── 5. Page functions ─────────────────────────────────────────────────────────
def run_analysis():
    show_analysis(matrix_dict, all_archetypes, records_data, DATA_DIR, TIMEFRAMES)

def run_meta_overview():
    show_meta_overview(matrix_dict, all_archetypes, records_data, DATA_DIR, TIMEFRAMES)

def run_simulator():
    show_simulator(matrix_dict, all_archetypes, records_data)

# ── 6. Navigation ─────────────────────────────────────────────────────────────
pg_analysis = st.Page(run_analysis,      title="Deck Analysis",         default=True)
pg_overview  = st.Page(run_meta_overview, title="Meta Overview")
pg_simulator = st.Page(run_simulator,    title="Tournament Simulator")

pg = st.navigation([pg_analysis, pg_overview, pg_simulator])
pg.run()
