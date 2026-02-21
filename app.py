import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.analytics import load_period_data, wilson_score_interval, calculate_polarity, calculate_expected_winrate, get_period_comparison

# Page Config
st.set_page_config(page_title="Brejkni to s Martinem", layout="wide")

# Theme / Colors
THEME = {
    "bg": "#0B1220",
    "surface-1": "#111A2B",
    "surface-2": "#0F1A2A",
    "border": "#22304A",
    "text": "#E6EAF2",
    "mutedText": "#A6B0C3",
    "subtleText": "#7E8AA3",
    "primary": "#7AA2F7",
    "secondary": "#7DCFFF",
    "accent": "#B4A1FF",
    "success": "#7EE787",
    "warning": "#F2C97D",
    "danger": "#FF8FA3",
    "info": "#8AB4F8",
}

# Custom CSS for UI polish
st.markdown(f"""
    <style>
    .main > div {{
        padding-top: 2rem;
        background-color: {THEME['bg']};
    }}
    [data-testid="stSidebar"] {{
        background-color: {THEME['surface-1']};
        border-right: 1px solid {THEME['border']};
    }}
    .stMetric {{
        background-color: {THEME['surface-2']};
        padding: 15px;
        border-radius: 10px;
        border: 1px solid {THEME['border']};
    }}
    div[data-testid="stExpander"] {{
        background-color: {THEME['surface-1']};
        border: 1px solid {THEME['border']};
    }}
    /* Global Text Styling */
    h1, h2, h3, h4, h5, h6, b, strong {{
        color: {THEME['text']} !important;
    }}
    .stMarkdown p, .stMarkdown label {{
        color: {THEME['mutedText']};
    }}
    /* Ensure tables have transparent or themed background */
    .stDataFrame, .stTable {{
        background-color: transparent !important;
    }}
    </style>
""", unsafe_allow_html=True)

# Helper for color coding win rates (Bold Text only)
def style_winrate(val):
    if val is None or val == "-": return ""
    try:
        if isinstance(val, str) and "%" in val:
            num = float(val.split("%")[0]) / 100
        else:
            num = float(val)
        
        # Color boundaries
        if num < 0.45: color = THEME["danger"]
        elif num < 0.49: color = THEME["warning"]
        elif num < 0.51: return "font-weight: bold; color: " + THEME["text"]
        elif num < 0.55: color = THEME["info"]
        else: color = THEME["success"]
        
        return f'color: {color}; font-weight: bold;'
    except:
        return ""

# Sidebar Content
st.sidebar.title("Brejkni to s Martinem")
st.sidebar.divider()
st.sidebar.info("Zdroj dat: [Duress Crew](https://data.duresscrew.com/)")

# Shared Data Loading
DATA_DIR = "data"
TIMEFRAMES = {
    "All Time": "all_time",
    "3 Months": "3_months",
    "6 Months": "6_months",
    "1 Year": "1_year",
    "2 Years": "2_years"
}

@st.cache_data
def get_data(period_key):
    period_val = TIMEFRAMES[period_key]
    return load_period_data(DATA_DIR, period_val)

# Global Filters
period_name = st.sidebar.selectbox("Globální časový rámec", list(TIMEFRAMES.keys()), index=0)
matrix_data, records_data = get_data(period_name)

all_archetypes = matrix_data["archetypes"]
matrix_dict = matrix_data["matrix"]

# Navigation
menu = ["Analýza Balíku", "Matchup matice", "Trendy", "Simulátor turnaje"]
choice = st.sidebar.radio("Navigace", menu, index=0)

# --- Matchup Matrix ---
if choice == "Matchup matice":
    st.title("Interaktivní Matchup matice")
    
    c1, c2 = st.columns([3, 1])
    with c1:
        selected_decks = st.multiselect("Vyberte balíky", all_archetypes, default=all_archetypes)
    with c2:
        min_games = st.slider("Minimální práh her", 0, 50, 5)
    
    if not selected_decks:
        st.warning("Prosím vyberte alespoň jeden balík.")
    else:
        hm_data = []
        for arch1 in selected_decks:
            row = []
            for arch2 in selected_decks:
                cell = matrix_dict.get(arch1, {}).get(arch2, {})
                total = cell.get("total_matches", 0)
                if total >= min_games:
                    row.append(cell.get("win_rate", 0.5))
                else:
                    row.append(None)
            hm_data.append(row)
            
        fig = px.imshow(
            hm_data,
            x=selected_decks,
            y=selected_decks,
            color_continuous_scale=[[0, THEME["danger"]], [0.5, THEME["border"]], [1, THEME["success"]]],
            labels=dict(color="Win Rate"),
            zmin=0.3, zmax=0.7,
            aspect="auto",
            text_auto='.1%'
        )
        fig.update_layout(
            height=700, 
            margin=dict(l=0, r=0, b=0, t=40),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color=THEME["text"]
        )
        st.plotly_chart(fig, use_container_width=True)
        st.info("Najeďte myší na buňky pro přesné win raty. Škála je centrovaná na 50%.")

# --- Deck Profiles ---
elif choice == "Analýza Balíku":
    st.title("Analýza Balíku")
    
    target_deck = st.selectbox("Vyberte balík (Select Deck)", all_archetypes)
    
    polarity = calculate_polarity(target_deck, matrix_dict, all_archetypes)
    st.metric("Index polarity", f"{polarity*100:.1f}%")
    st.caption("Nižší = Stabilní (všechny matchupy podobné), Vyšší = Kámen-Nůžky-Papír (velké rozdíly)")

    # Matchup Breakdown
    row_data = matrix_dict.get(target_deck, {})
    prof_rows = []
    for other in all_archetypes:
        if other == target_deck: continue
        cell = row_data.get(other, {})
        total = cell.get("total_matches", 0)
        if total > 0:
            wr = cell.get("win_rate", 0)
            l, u = wilson_score_interval(cell['wins'], total)
            prof_rows.append({
                "Opponent": other,
                "Win Rate": wr,
                "Confidence (95%)": f"{l*100:.1f}% - {u*100:.1f}%",
                "Record": f"{cell['wins']}W-{cell['losses']}L",
                "Games": total
            })
            
    df_prof = pd.DataFrame(prof_rows).sort_values("Win Rate", ascending=False)
    
    st.subheader("Přehled matchupů")
    st.dataframe(
        df_prof.style.applymap(style_winrate, subset=["Win Rate"]).format({"Win Rate": "{:.1%}"}),
        use_container_width=True, hide_index=True
    )

    st.divider()
    
    col_best, col_worst = st.columns(2)
    with col_best:
        st.subheader("Top 5 Nejlepší matchupy")
        st.dataframe(
            df_prof.head(5)[["Opponent", "Win Rate", "Record"]].style.applymap(style_winrate, subset=["Win Rate"]).format({"Win Rate": "{:.1%}"}),
            use_container_width=True, hide_index=True
        )
        
    with col_worst:
        st.subheader("Top 5 Nehorší matchupy")
        st.dataframe(
            df_prof.tail(5)[["Opponent", "Win Rate", "Record"]].style.applymap(style_winrate, subset=["Win Rate"]).format({"Win Rate": "{:.1%}"}),
            use_container_width=True, hide_index=True
        )

# --- Meta Trends ---
elif choice == "Trendy":
    st.title("Srovnání vývoje mety")
    st.write("Vývoj win rate napříč různými vzorky času.")
    
    with st.spinner("Zpracování dat..."):
        pivot_wr, games_df = get_period_comparison(DATA_DIR, TIMEFRAMES)
    
    if pivot_wr.empty:
        st.error("Nepodařilo se načíst data trendů.")
    else:
        min_total_games = st.slider("Minimální celkový počet her", 0, 500, 100)
        total_games_all = games_df.sum(axis=1)
        top_decks_trend = total_games_all[total_games_all >= min_total_games].index.tolist()
        
        if not top_decks_trend:
            st.warning("Žádné balíky neodpovídají threshold.")
        else:
            selected_trend_decks = st.multiselect("Vyberte balíky pro analýzu", top_decks_trend, default=top_decks_trend[:5])
            
            ordered_periods = ["3 Months", "6 Months", "1 Year", "2 Years", "All Time"]
            existing_periods = [p for p in ordered_periods if p in pivot_wr.columns]
            trend_df = pivot_wr.loc[selected_trend_decks][existing_periods].T
            
            fig_trend = px.line(
                trend_df, 
                markers=True,
                title="Vývoj Win Rate",
                labels={"value": "Win Rate", "index": "Období"},
                range_y=[0.3, 0.7]
            )
            fig_trend.add_hline(y=0.5, line_dash="dash", line_color=THEME["subtleText"])
            fig_trend.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color=THEME["text"]
            )
            st.plotly_chart(fig_trend, use_container_width=True)
            
            st.subheader("Surová data win ratů")
            st.dataframe(
                pivot_wr.loc[selected_trend_decks].style.applymap(style_winrate).format("{:.1%}"),
                use_container_width=True
            )

# --- Simulator ---
elif choice == "Simulátor turnaje":
    st.title("Strategický simulátor turnaje")
    st.markdown("Predikce výkonu v závislosti na očekávaném složení pole.")
    
    st.subheader("1. Nastavení očekávaného fieldu")
    meta_shares = {}
    total_share = 0
    
    top_decks = [r["archetype"] for r in sorted(records_data, key=lambda x: x.get("total_matches", 0), reverse=True)[:8]]
    
    cols = st.columns(4)
    for i, deck in enumerate(top_decks):
        with cols[i % 4]:
            share = st.number_input(f"{deck} %", 0, 100, 10 if i < 3 else 5, key=f"sim_{deck}")
            meta_shares[deck] = share / 100
            total_share += share
            
    st.markdown(f"**Zmapováno pole: {total_share}%**")
    if total_share > 100:
        st.error("Celkový podíl přesahuje 100%!")
    
    if st.button("Vypočítat očekávaný výkon (Projected EV)", type="primary"):
        if total_share == 0:
            st.error("Prosím definujte alespoň jeden balík.")
        else:
            evs = calculate_expected_winrate(meta_shares, matrix_dict, all_archetypes)
            ev_df = pd.DataFrame(list(evs.items()), columns=["Select Deck", "Očekávaná Win Rate"])
            ev_df = ev_df.sort_values("Očekávaná Win Rate", ascending=False)
            
            st.divider()
            st.subheader("Výsledky projekce")
            
            c1, c2 = st.columns([1, 2])
            with c1:
                st.dataframe(
                    ev_df.head(15).style.applymap(style_winrate, subset=["Očekávaná Win Rate"]).format({"Očekávaná Win Rate": "{:.1%}"}),
                    use_container_width=True, hide_index=True
                )
            with c2:
                fig_ev = px.bar(
                    ev_df.head(10), 
                    x="Select Deck", 
                    y="Očekávaná Win Rate",
                    color="Očekávaná Win Rate",
                    color_continuous_scale=[[0, THEME["danger"]], [0.5, THEME["border"]], [1, THEME["success"]]],
                    range_color=[0.4, 0.6]
                )
                fig_ev.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color=THEME["text"]
                )
                st.plotly_chart(fig_ev, use_container_width=True)
