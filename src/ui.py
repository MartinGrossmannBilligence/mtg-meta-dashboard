import streamlit as st

# DURESS MONO Design Tokens
THEME = {
    "bg": "#0B0B0B",
    "surface": "#111111",
    "surface2": "#151515",
    "border": "#222222",
    "text": "#F5F5F5",
    "muted": "#B8B8B8",
    "faint": "#8A8A8A",
    "invertBg": "#F5F5F5",
    "invertText": "#0B0B0B",
    "focus": "#8EA7B6",
    # Data viz (muted)
    "success": "#6BC78E",
    "danger": "#C76B6B",
    "warning": "#C7B36B",
}

def apply_custom_css():
    st.markdown(f"""
        <style>
        /* Global & Typography */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Playfair+Display:wght@700&display=swap');
        
        * {{
            font-variant-numeric: tabular-nums;
        }}
        
        .block-container {{
            padding-top: 1.2rem;
            background-color: {THEME['bg']};
        }}
        
        /* Headers */
        h1 {{
            font-family: 'Playfair Display', Georgia, serif !important;
            font-size: 44px !important;
            font-weight: 700 !important;
            line-height: 1.1 !important;
            margin-bottom: 8px !important;
            color: {THEME['text']} !important;
        }}
        h2 {{
            font-size: 28px !important;
            font-weight: 600 !important;
            color: {THEME['text']} !important;
        }}
        h3 {{
            font-size: 20px !important;
            font-weight: 600 !important;
            color: {THEME['text']} !important;
        }}
        
        /* Sidebar & Navigation */
        [data-testid="stSidebar"] {{
            background-color: {THEME['surface']};
            border-right: 1px solid {THEME['border']};
        }}
        
        /* ── Sidebar nav: inject app title + subtitle ABOVE page links via ::before/after ── */
        [data-testid="stSidebarNav"] {{
            padding-top: 100px;  /* make room for title + subtitle */
            position: relative;
        }}
        /* Main Title */
        [data-testid="stSidebarNav"]::before {{
            content: "Premodern Meta Lab";
            display: block;
            position: absolute;
            top: 20px;
            left: 16px;
            right: 16px;
            font-family: 'Playfair Display', Georgia, serif;
            font-size: 20px;
            font-weight: 700;
            color: {THEME['text']};
            letter-spacing: -0.4px;
        }}
        /* Subtitle line + Divider (we remove ::after and instead inject real HTML for links) */
        .sidebar-subtitle {{
            position: absolute;
            top: 54px;
            left: 16px;
            right: 16px;
            padding-bottom: 12px;
            font-family: 'Inter', sans-serif;
            font-size: 11px;
            color: {THEME['faint']};
            border-bottom: 1px solid {THEME['border']};
            z-index: 100;
        }}
        .sidebar-subtitle a {{
            color: {THEME['faint']} !important;
            text-decoration: underline !important;
            text-decoration-color: {THEME['border']} !important;
        }}
        .sidebar-subtitle a:hover {{
            color: {THEME['text']} !important;
        }}
        [data-testid="stSidebarNav"] ul {{
            padding-left: 0;
        }}
        [data-testid="stSidebarNav"] li {{
            margin-bottom: 4px;
        }}
        [data-testid="stSidebarNav"] a,
        [data-testid="stSidebarNav"] span {{
            background-color: transparent !important;
            color: {THEME['muted']} !important;
            border-radius: 4px;
            padding: 8px 12px;
            font-family: monospace;
        }}
        [data-testid="stSidebarNav"] a:hover {{
            background-color: {THEME['surface2']} !important;
            color: {THEME['text']} !important;
        }}
        [data-testid="stSidebarNav"] a[aria-current="page"] {{
            background-color: {THEME['surface2']} !important;
            color: {THEME['text']} !important;
            border-left: 2px solid {THEME['text']};
        }}

        /* Components Card Look */
        [data-testid="stMetric"], 
        [data-testid="stDataFrame"],
        div[data-testid="stVerticalBlock"] > div:has(> [data-testid="stPlotlyChart"]) {{
            background-color: {THEME['surface']} !important;
            border: 1px solid {THEME['border']} !important;
            border-radius: 10px !important;
            padding: 12px !important;
            box-shadow: none !important;
        }}

        /* Buttons (Invert Hover) */
        .stButton > button {{
            background: transparent !important;
            border: 1px solid {THEME['border']} !important;
            color: {THEME['text']} !important;
            border-radius: 10px !important;
            transition: all 0.2s ease;
            font-weight: 500;
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

        /* Inputs / Selects */
        .stSelectbox div[data-baseweb="select"], 
        .stMultiSelect div[data-baseweb="select"],
        .stNumberInput input {{
            background-color: {THEME['surface']} !important;
            border: 1px solid {THEME['border']} !important;
            color: {THEME['text']} !important;
        }}
        
        /* Fix multiselect tags — primaryColor=white causes white-on-white */
        [data-baseweb="tag"] {{
            background-color: {THEME['surface2']} !important;
            border: 1px solid {THEME['border']} !important;
            color: {THEME['text']} !important;
        }}
        [data-baseweb="tag"] span {{
            color: {THEME['text']} !important;
        }}
        /* Tag close button */
        [data-baseweb="tag"] [role="presentation"] {{
            color: {THEME['muted']} !important;
        }}
        
        /* Pills / Links block */
        .source-pill {{
            font-size: 13px;
            padding: 4px 12px;
            border-radius: 12px;
            background: {THEME['surface2']};
            border: 1px solid {THEME['border']};
            color: {THEME['text']};
            text-decoration: none;
            display: inline-block;
            margin-top: 16px;
        }}
        .links-block {{
            font-family: monospace;
            font-size: 14px;
            color: {THEME['muted']};
        }}
        .links-title {{
            font-weight: bold;
            letter-spacing: 1px;
            color: {THEME['text']};
            margin-bottom: 8px;
        }}

        /* Table custom appearance */
        [data-testid="stDataFrame"] table {{
            border-collapse: collapse;
        }}
        [data-testid="stDataFrame"] td, [data-testid="stDataFrame"] th {{
            border-bottom: 1px solid {THEME['border']} !important;
        }}
        </style>
    """, unsafe_allow_html=True)

def style_winrate(val):
    """Muted data colors for win rates."""
    if val is None or val == "-" or val == "—": return ""
    try:
        if isinstance(val, str) and "%" in val:
            num = float(val.split("%")[0]) / 100
        else:
            num = float(val)
        
        # Color boundaries (Muted palette)
        if num < 0.45: color = THEME["danger"]
        elif num < 0.49: color = THEME["warning"]
        elif num < 0.51: return f'color: {THEME["text"]}; font-weight: bold;'
        elif num > 0.55: color = THEME["success"]
        else: color = THEME["text"]
        
        return f'color: {color}; font-weight: bold;'
    except:
        return ""
