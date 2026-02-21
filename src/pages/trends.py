import streamlit as st
import pandas as pd
import plotly.express as px
from src.analytics import get_period_comparison
from src.ui import THEME, style_winrate

def show_trends(data_dir, timeframes):
    st.title("Meta Trendy")
    st.markdown("Srovnání výkonnosti balíků napříč různými časovými úseky.")
    
    with st.spinner("Analyzuji historii..."):
        pivot_wr, games_df = get_period_comparison(data_dir, timeframes)
    
    if pivot_wr.empty:
        st.error("Nepodařilo se načíst data trendů.")
        return

    # Filter by total games
    min_total_games = st.slider("Minimální celkový počet her za celé období", 0, 500, 100)
    total_games_all = games_df.sum(axis=1)
    top_decks = total_games_all[total_games_all >= min_total_games].index.tolist()
    
    if not top_decks:
        st.warning("Žádné balíky neodpovídají nastavenému filtru.")
        return

    selected_decks = st.multiselect("DECKS FOR COMPARISON", top_decks, default=top_decks[:5])
    
    if not selected_decks:
        st.info("Vyberte alespoň jeden balík pro zobrazení grafu.")
        return

    # Prepare trend DF
    ordered_periods = list(timeframes.keys())
    existing_periods = [p for p in ordered_periods if p in pivot_wr.columns]
    trend_df = pivot_wr.loc[selected_decks][existing_periods].T
    
    # --- TREND CHART ---
    fig = px.line(
        trend_df, 
        markers=True,
        labels={"value": "Win Rate", "index": "Období"},
        template="plotly_dark",
        color_discrete_sequence=px.colors.qualitative.Safe
    )
    
    fig.add_hline(y=0.5, line_dash="dash", line_color=THEME["faint"], annotation_text="Break-even (50%)")
    
    fig.update_layout(
        height=500,
        hovermode="x unified",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color=THEME["text"],
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=0, r=0, t=20, b=0)
    )
    
    fig.update_yaxes(tickformat=".0%", range=[0.3, 0.7])
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # --- RAW DATA TABLE ---
    st.subheader("Surová data win ratů")
    raw_display = pivot_wr.loc[selected_decks][existing_periods]
    # Replace None/NaN with "—"
    raw_display = raw_display.fillna("—")
    
    st.dataframe(
        raw_display.style.applymap(style_winrate),
        use_container_width=True
    )
    st.caption("Poznámka: '—' značí nedostatek dat pro dané období.")
