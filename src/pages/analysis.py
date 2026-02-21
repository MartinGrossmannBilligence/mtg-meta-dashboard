import streamlit as st
import pandas as pd
import plotly.express as px
from src.analytics import load_period_data, wilson_score_interval, calculate_polarity
from src.ui import THEME, style_winrate

def show_analysis(matrix_dict, all_archetypes, records_data):
    st.markdown("<h1>Analýza Balíku</h1>", unsafe_allow_html=True)
    st.markdown('<p style="color:#8A8A8A; font-size:13px; margin-top:-20px; margin-bottom:24px;">Premodern Metagame · Data: Duress Crew · Last Update: Feb 2026</p>', unsafe_allow_html=True)
    
    # Horizontal Filter Bar
    target_deck = st.selectbox("SELECT PRIMARY DECK", all_archetypes)
    
    # --- KPI ROW ---
    row_data = matrix_dict.get(target_deck, {})
    
    # Calculate overall stats for this deck from records_data
    deck_record = next((r for r in records_data if r["archetype"] == target_deck), {})
    overall_wr = deck_record.get("win_rate", 0)
    total_games = deck_record.get("total_matches", 0)
    
    # Prepare matchup data
    prof_rows = []
    for other in all_archetypes:
        if other == target_deck: continue
        cell = row_data.get(other, {})
        total = cell.get("total_matches", 0)
        if total > 0:
            wr = cell.get("win_rate", 0.5)
            prof_rows.append({
                "Opponent": other,
                "Win Rate": wr,
                "Record": f"{cell['wins']}W - {cell['losses']}L",
                "Games": total
            })
    
    df_prof = pd.DataFrame(prof_rows).sort_values("Win Rate", ascending=False)
    
    # Best/Worst for KPIs
    best_name = df_prof.iloc[0]["Opponent"] if not df_prof.empty else "N/A"
    worst_name = df_prof.iloc[-1]["Opponent"] if not df_prof.empty else "N/A"
    polarity = calculate_polarity(target_deck, matrix_dict, all_archetypes)
    
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    kpi1.metric("Celková Win Rate", f"{overall_wr:.1%}")
    kpi2.metric("Počet her", total_games)
    kpi3.metric("Nejlepší matchup", best_name)
    kpi4.metric("Nejhorší matchup", worst_name)
    kpi5.metric("Index polarity", f"{polarity*100:.1f}%")
    
    st.divider()
    
    # --- DISTRIBUTION CHART (full row) ---
    c_chart, c_spacer = st.columns([1, 2])
    with c_chart:
        st.subheader("Distribuce matchupů")
        if not df_prof.empty:
            df_prof["Bracket"] = pd.cut(
                df_prof["Win Rate"],
                bins=[0, 0.45, 0.55, 1.0],
                labels=["Špatné (<45%)", "Vyrovnané (45-55%)", "Dobré (>55%)"]
            )
            dist = df_prof["Bracket"].value_counts().reindex(["Špatné (<45%)", "Vyrovnané (45-55%)", "Dobré (>55%)"]).reset_index()
            dist.columns = ["Kategorie", "Počet"]
            fig_dist = px.bar(
                dist, x="Kategorie", y="Počet",
                color="Kategorie",
                color_discrete_map={
                    "Špatné (<45%)": THEME["danger"],
                    "Vyrovnané (45-55%)": THEME["warning"],
                    "Dobré (>55%)": THEME["success"]
                },
                template="plotly_dark"
            )
            fig_dist.update_layout(
                showlegend=False, height=280,
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=20, b=0),
                xaxis_title="", yaxis_title="POČET"
            )
            st.plotly_chart(fig_dist, use_container_width=True)
        else:
            st.info("Nedostatek dat.")
    
    st.divider()
    
    # --- FULL MATCHUP TABLE ---
    st.subheader("Všechny matchupy")
    if not df_prof.empty:
        st.dataframe(
            df_prof[["Opponent", "Win Rate", "Record", "Games"]]
            .style.applymap(style_winrate, subset=["Win Rate"])
            .format({"Win Rate": "{:.1%}"}),
            use_container_width=True, hide_index=True
        )
    
    st.divider()
    
    # --- TOP 5 / BOTTOM 5 ---
    col_best, col_worst = st.columns(2)
    with col_best:
        st.subheader("Top 5 nejlepší matchupy")
        if not df_prof.empty:
            st.dataframe(
                df_prof.head(5)[["Opponent", "Win Rate", "Record"]]
                .style.applymap(style_winrate, subset=["Win Rate"])
                .format({"Win Rate": "{:.1%}"}),
                use_container_width=True, hide_index=True
            )
    with col_worst:
        st.subheader("Top 5 nejhorší matchupy")
        if not df_prof.empty:
            st.dataframe(
                df_prof.tail(5)[["Opponent", "Win Rate", "Record"]]
                .style.applymap(style_winrate, subset=["Win Rate"])
                .format({"Win Rate": "{:.1%}"}),
                use_container_width=True, hide_index=True
            )
