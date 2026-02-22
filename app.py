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

# ── 3. Sidebar ─────────────────────────────────────────────────────
# st.logo() pins content at the very top of the sidebar, above the navigation links.
# We inject a tiny HTML "logo" that displays our app name + data source.
st.logo(
    image="data:image/svg+xml;base64,",  # 1-px transparent placeholder
    link="https://data.duresscrew.com/",
    size="small",
)

# The navigation links are rendered by Streamlit at the top of the sidebar.
# We put remaining sidebar controls below.
with st.sidebar:
    # Branding rendered with custom CSS; it is injected above the nav via the
    # ::before trick on [data-testid="stSidebar"].
    st.markdown(
        '<p style="font-size:19px;font-weight:700;margin:0 0 2px 0;letter-spacing:-0.4px;">Premodern Meta Lab</p>'
        '<p style="color:#8A8A8A;font-size:12px;margin:0 0 12px 0;">'
        'Based on <a href="https://data.duresscrew.com/" style="color:#8A8A8A;">Duress Crew</a> data</p>',
        unsafe_allow_html=True,
    )
    st.divider()
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
