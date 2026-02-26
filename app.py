import streamlit as st
import pandas as pd
from src.analytics import load_period_data, calculate_expected_winrate
from src.ui import apply_custom_css, THEME
from src.pages.analysis import show_analysis
from src.pages.meta_overview import show_meta_overview
from src.pages.simulator import show_simulator

# ── 1. Page Config ────────────────────────────────────────────────────────────
st.set_page_config(page_title="MTG Premodern Lab", page_icon="assets/favicon.png", layout="wide")
apply_custom_css()

# ── 2. Constants ──────────────────────────────────────────────────────────────
DATA_DIR = "data"
TIMEFRAMES = {
    "2Y": "all_time",
    "1Y": "1_year",
    "6M": "mtgdecks_matrix_6_months",
    "2M": "mtgdecks_matrix_2_months",
}

@st.cache_data(ttl=3600)
def get_cached_period_data(period_key):
    # Cache busting: v8
    return load_period_data(DATA_DIR, TIMEFRAMES[period_key])

# "Premodern Meta Lab" title is injected above the nav links via CSS ::before
# in apply_custom_css().
with st.sidebar:
    st.markdown('<p style="font-size: 0.85rem; margin-bottom: 0.2rem; opacity: 0.7;">Choose Timeframe</p>', unsafe_allow_html=True)
    period_name = st.segmented_control(
        "Choose Timeframe", 
        options=list(TIMEFRAMES.keys()), 
        default="2Y",
        label_visibility="collapsed"
    )
    st.divider()
    
    # Push items to bottom
    st.markdown('<div style="flex-grow:1;"></div><br><br><br>', unsafe_allow_html=True)
    
    st.markdown(
        '<div class="source-pill">This app is based on <a href="https://mtgdecks.net/Premodern" target="_blank" style="text-decoration: underline;">MTGDecks.net</a> data.</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="source-pill" style="margin-top:10px;">Feel free to contact me via <a href="mailto:grossmann.martin.cz@gmail.com">Email</a> or <a href="https://m.me/martin.grossmann.5" target="_blank">Messenger</a>. Martin Grossmann</div>',
        unsafe_allow_html=True,
    )


# ── 4. Data ───────────────────────────────────────────────────────────────────
try:
    matrix_data, records_data = get_cached_period_data(period_name)
    all_archetypes = matrix_data["archetypes"]
    tiers_dict     = matrix_data.get("tiers", {})
except Exception as e:
    st.error(f"Failed to load data: {e}")
    st.stop()

# ── 5. Page functions ─────────────────────────────────────────────────────────
def run_analysis():
    show_analysis(matrix_data, all_archetypes, records_data, DATA_DIR, TIMEFRAMES)

def run_meta_overview():
    show_tier_filter = period_name not in ["6 Months", "2 Months"]
    show_meta_overview(matrix_data, all_archetypes, records_data, DATA_DIR, TIMEFRAMES, tiers_dict, show_tier_filter)

def run_simulator():
    show_simulator(matrix_data, all_archetypes, records_data)

# ── 6. Navigation ─────────────────────────────────────────────────────────────
pg_overview  = st.Page(run_meta_overview, title="Meta Overview",      default=True)
pg_analysis = st.Page(run_analysis,      title="Deck Analysis")
pg_simulator = st.Page(run_simulator,    title="Tournament Simulator")

pg = st.navigation([pg_overview, pg_analysis, pg_simulator])

pg.run()
