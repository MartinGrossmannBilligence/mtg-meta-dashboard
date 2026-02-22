import streamlit as st
from src.bg_data import BG_TOG_V10_B64

# DURESS MONO Design Tokens
THEME = {
    "bg":          "#181818",
    "surface":     "#1F1F1F",
    "surface2":    "#252525",
    "border":      "#2E2E2E",
    "text":        "#F5F5F5",
    "muted":       "#B8B8B8",
    "faint":       "#8A8A8A",
    "invertBg":    "#F5F5F5",
    "invertText":  "#181818",
    "focus":       "#8EA7B6",
    # Data viz (muted)
    "success":     "#6BC78E",
    "danger":      "#C76B6B",
    "warning":     "#C7B36B",
}

def apply_custom_css():
    st.markdown(f"""
        <style>
        /* ── Global & Typography ─────────────────────────────────────────── */
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&display=swap');

        * {{
            font-variant-numeric: tabular-nums;
        }}

        html, body, [class*="css"] {{
            font-family: 'IBM Plex Mono', monospace !important;
        }}

        .block-container {{
            padding-top: 24px !important;
            padding-bottom: 48px !important;
            max-width: 1400px;
            background-color: transparent;
        }}

        /* ── Background color ─────────────────────────────────────────────── */
        [data-testid="stApp"] {{
            background-image: url("data:image/jpeg;base64,{BG_TOG_V10_B64}");
            background-size: cover;
            background-position: top center;
            background-attachment: fixed;
            background-repeat: no-repeat;
            background-color: #181818;
        }}
        /* Ensure intermediate container is transparent so we see the stApp background */
        [data-testid="stAppViewContainer"] {{
            background-color: transparent;
        }}
        [data-testid="stApp"]::before {{
            content: "";
            position: fixed;
            inset: 0;
            background-color: rgba(24, 24, 24, 0.65);
            pointer-events: none;
            z-index: 0;
        }}
        /* Make header completely see-through to reveal background underneath */
        [data-testid="stHeader"] {{
            background-color: transparent !important;
        }}

        /* ── Typography hierarchy ─────────────────────────────────────────── */
        h1 {{
            font-family: 'IBM Plex Mono', monospace !important;
            font-size: 36px !important;
            font-weight: 400 !important;
            line-height: 1.1 !important;
            margin-bottom: 4px !important;
            margin-top: 0 !important;
            color: {THEME['text']} !important;
            letter-spacing: -0.5px !important;
        }}
        h2 {{
            font-family: 'IBM Plex Mono', monospace !important;
            font-size: 24px !important;
            font-weight: 600 !important;
            color: {THEME['text']} !important;
            margin-top: 0 !important;
            margin-bottom: 8px !important;
        }}
        h3 {{
            font-family: 'IBM Plex Mono', monospace !important;
            font-size: 18px !important;
            font-weight: 600 !important;
            color: {THEME['text']} !important;
            margin-top: 0 !important;
            margin-bottom: 8px !important;
        }}

        /* ── Dividers ─────────────────────────────────────────────────────── */
        hr {{
            margin-top: 12px !important;
            margin-bottom: 12px !important;
            border-color: {THEME['border']} !important;
        }}
        div[data-testid="stVerticalBlock"] > div {{
            padding-bottom: 0.1rem;
        }}

        /* ── Hide Streamlit footer & main menu ────────────────────────────── */
        #MainMenu {{ visibility: hidden; }}
        footer {{ visibility: hidden; }}
        
        /* ── Sidebar shell ────────────────────────────────────────────────── */
        [data-testid="stSidebar"] {{
            background-color: {THEME['surface']};
            border-right: 1px solid {THEME['border']};
        }}

        /* ── Sidebar Nav: title injected via ::before ─────────────────────── */
        [data-testid="stSidebarNav"] {{
            padding-top: 72px;
            position: relative;
        }}
        [data-testid="stSidebarNav"]::before {{
            content: "Premodern Meta Lab";
            display: block;
            position: absolute;
            top: 16px;
            left: 16px;
            right: 16px;
            font-family: 'IBM Plex Mono', monospace;
            font-size: 18px;
            font-weight: 600;
            color: {THEME['text']};
            letter-spacing: -0.3px;
            line-height: 1.2;
            white-space: nowrap;
        }}

        [data-testid="stSidebarNav"] ul {{
            padding-left: 0;
            margin: 0;
        }}
        [data-testid="stSidebarNav"] li {{
            margin-bottom: 2px;
            list-style: none;
        }}
        [data-testid="stSidebarNav"] a,
        [data-testid="stSidebarNav"] span {{
            background-color: transparent !important;
            color: {THEME['muted']} !important;
            border-radius: 10px !important;
            padding: 7px 12px !important;
            font-family: 'IBM Plex Mono', monospace;
            font-size: 14px;
            display: block;
            transition: background 0.15s, color 0.15s;
        }}
        [data-testid="stSidebarNav"] a:hover {{
            background-color: {THEME['surface2']} !important;
            color: {THEME['text']} !important;
        }}
        [data-testid="stSidebarNav"] a[aria-current="page"] {{
            background-color: #2A2A2A !important;
            color: {THEME['text']} !important;
            border-left: 2px solid {THEME['text']};
            padding-left: 10px !important;
            font-weight: 600 !important;
        }}

        /* ── Sidebar widgets (Timeframe etc.) – tighten gap after nav ──────── */
        [data-testid="stSidebarContent"] {{
            display: flex;
            flex-direction: column;
        }}
        /* Timeframe label */
        [data-testid="stSidebar"] .stSelectbox label {{
            font-family: 'IBM Plex Mono', monospace;
            font-size: 11px;
            color: {THEME['faint']} !important;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }}

        /* ── KPI / Metric cards ───────────────────────────────────────────── */
        [data-testid="stMetric"] {{
            background-color: {THEME['surface']} !important;
            border: 1px solid {THEME['border']} !important;
            border-radius: 10px !important;
            padding: 16px !important;
            box-shadow: none !important;
        }}
        [data-testid="stMetricLabel"] {{
            font-family: 'IBM Plex Mono', monospace !important;
            font-size: 12px !important;
            color: {THEME['faint']} !important;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }}
        [data-testid="stMetricValue"] {{
            font-family: 'IBM Plex Mono', monospace !important;
            font-size: 28px !important;
            font-weight: 700 !important;
            color: {THEME['text']} !important;
        }}

        /* ── DataFrames / Tables ──────────────────────────────────────────── */
        [data-testid="stDataFrame"] {{
            background-color: {THEME['surface']} !important;
            border: 1px solid {THEME['border']} !important;
            border-radius: 10px !important;
            padding: 0 !important;
            box-shadow: none !important;
        }}
        [data-testid="stDataFrame"] table {{
            border-collapse: collapse;
        }}
        [data-testid="stDataFrame"] td, [data-testid="stDataFrame"] th {{
            border-bottom: 1px solid {THEME['border']} !important;
            padding: 8px 12px !important;
            font-family: 'IBM Plex Mono', monospace !important;
            font-size: 13px !important;
        }}
        [data-testid="stDataFrame"] th {{
            color: {THEME['muted']} !important;
            font-size: 11px !important;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            background-color: {THEME['surface2']} !important;
        }}

        /* ── Plotly chart wrapper card ────────────────────────────────────── */
        div[data-testid="stVerticalBlock"] > div:has(> [data-testid="stPlotlyChart"]) {{
            background-color: {THEME['surface']} !important;
            border: 1px solid {THEME['border']} !important;
            border-radius: 10px !important;
            padding: 12px !important;
            box-shadow: none !important;
        }}

        /* ── Buttons ──────────────────────────────────────────────────────── */
        .stButton > button {{
            background: transparent !important;
            border: 1px solid {THEME['border']} !important;
            color: {THEME['text']} !important;
            border-radius: 10px !important;
            font-family: 'IBM Plex Mono', monospace !important;
            font-size: 14px !important;
            font-weight: 500 !important;
            padding: 8px 20px !important;
            transition: all 0.15s ease;
        }}
        .stButton > button:hover {{
            background: {THEME['invertBg']} !important;
            color: {THEME['invertText']} !important;
            border-color: {THEME['invertBg']} !important;
        }}
        .stButton > button:focus {{
            outline: 2px solid {THEME['focus']} !important;
            outline-offset: 2px !important;
        }}

        /* ── Selectbox / Inputs ───────────────────────────────────────────── */
        .stSelectbox div[data-baseweb="select"],
        .stMultiSelect div[data-baseweb="select"],
        .stNumberInput input {{
            background-color: {THEME['surface']} !important;
            border: 1px solid {THEME['border']} !important;
            border-radius: 10px !important;
            color: {THEME['text']} !important;
            font-family: 'IBM Plex Mono', monospace !important;
        }}
        .stSelectbox div[data-baseweb="select"] {{
            font-size: 15px !important;
            font-weight: 600 !important;
        }}

        /* Fix multiselect tags */
        [data-baseweb="tag"] {{
            background-color: {THEME['surface2']} !important;
            border: 1px solid {THEME['border']} !important;
            color: {THEME['text']} !important;
            border-radius: 6px !important;
        }}
        [data-baseweb="tag"] span {{ color: {THEME['text']} !important; }}
        [data-baseweb="tag"] [role="presentation"] {{ color: {THEME['muted']} !important; }}

        /* ── Tabs ─────────────────────────────────────────────────────────── */
        [data-testid="stTabs"] [data-baseweb="tab-list"] {{
            gap: 4px;
            border-bottom: 1px solid {THEME['border']};
            background: transparent;
        }}
        [data-testid="stTabs"] [data-baseweb="tab"] {{
            background: transparent !important;
            color: {THEME['muted']} !important;
            font-family: 'IBM Plex Mono', monospace !important;
            font-size: 14px !important;
            border: none !important;
            border-radius: 0 !important;
            padding: 8px 16px !important;
            border-bottom: 2px solid transparent !important;
        }}
        [data-testid="stTabs"] [data-baseweb="tab"]:hover {{
            color: {THEME['text']} !important;
            background: {THEME['surface2']} !important;
        }}
        [data-testid="stTabs"] [aria-selected="true"] {{
            color: {THEME['text']} !important;
            border-bottom: 2px solid {THEME['text']} !important;
            background: transparent !important;
        }}

        /* ── Sliders ──────────────────────────────────────────────────────── */
        [data-testid="stSlider"] label {{
            font-family: 'IBM Plex Mono', monospace !important;
            font-size: 12px !important;
            color: {THEME['muted']} !important;
        }}

        /* ── Selectbox un-bold fix ────────────────────────────────────────── */
        div[data-baseweb="select"] span {{
            font-weight: 400 !important;
        }}

        /* ── Info / Warning boxes ─────────────────────────────────────────── */
        [data-testid="stInfo"], [data-testid="stWarning"] {{
            border-radius: 10px !important;
            border: 1px solid {THEME['border']} !important;
            background-color: {THEME['surface']} !important;
        }}

        /* ── Source link (small muted footer in sidebar) ──────────────────── */
        .source-pill {{
            font-size: 12px;
            color: {THEME['faint']};
            font-family: 'IBM Plex Mono', monospace;
        }}
        .source-pill a {{
            color: {THEME['faint']};
            text-decoration: underline;
            text-underline-offset: 2px;
        }}
        </style>
    """, unsafe_allow_html=True)


def style_winrate(val):
    """Muted data colors for win rates."""
    if val is None or val == "-" or val == "—":
        return ""
    try:
        if isinstance(val, str) and "%" in val:
            num = float(val.split("%")[0]) / 100
        else:
            num = float(val)

        if num < 0.45:   color = THEME["danger"]
        elif num < 0.49: color = THEME["warning"]
        elif num < 0.51: return f'color: {THEME["text"]}; font-weight: bold;'
        elif num > 0.55: color = THEME["success"]
        else:            color = THEME["text"]

        return f'color: {color}; font-weight: bold;'
    except:
        return ""
