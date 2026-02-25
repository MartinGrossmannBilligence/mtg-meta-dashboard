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
    "All Time": "all_time",
    "1 Year":   "1_year",
    "6 Months": "mtgdecks_matrix_6_months",
    "2 Months": "mtgdecks_matrix_2_months",
}

@st.cache_data(ttl=3600)
def get_cached_period_data(period_key):
    # Cache busting: v6
    return load_period_data(DATA_DIR, TIMEFRAMES[period_key])

# "Premodern Meta Lab" title is injected above the nav links via CSS ::before
# in apply_custom_css().
with st.sidebar:

    period_name = st.selectbox(
        "Choose Timeframe", 
        list(TIMEFRAMES.keys()), 
        index=0,
        help="Aggregated performance data summarizing all recorded matches within the selected time window (e.g., last 6 months or 1 year)."
    )
    st.divider()
    
    help_text = (
        "Data Sources & Mapping\n\n"
        "• 6 Months & 2 Months data, along with the overall Meta Share metric, are sourced from MTGDecks.net. "
        "These provide a highly granular view of recent tournament results, including a larger proportion of lower-tier decks.\n\n"
        "• All-Time & 1 Year data is sourced from the Duress Crew data project, providing a robust "
        "historical foundation for matchups.\n\n"
        "• To ensure continuity, decks from both sources are mapped together so you can analyze a deck's "
        "performance seamlessly across all timeframes."
    )
    
    st.markdown(
        '<div class="source-pill">This app is based on data from <b>MTGDecks.net</b> & <a href="https://data.duresscrew.com/" target="_blank">Duress Crew</a>.</div>',
        unsafe_allow_html=True,
        help=help_text
    )


    st.markdown('<div style="flex-grow:1;"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="source-pill" style="margin-top:auto;"><span style="color:#BEBEBE;">Created by Martin Grossmann</span><br>Feel free to contact me via <a href="mailto:grossmann.martin.cz@gmail.com">Email</a> or <a href="https://m.me/martin.grossmann.5" target="_blank">Messenger</a></div>',
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
pg_analysis = st.Page(run_analysis,      title="Deck Analysis",         default=True)
pg_overview  = st.Page(run_meta_overview, title="Meta Overview")
pg_simulator = st.Page(run_simulator,    title="Tournament Simulator")

pg = st.navigation([pg_analysis, pg_overview, pg_simulator])
pg.run()
