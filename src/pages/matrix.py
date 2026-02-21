import streamlit as st
import pandas as pd
import plotly.express as px
from src.ui import THEME

def show_matrix(matrix_dict, all_archetypes):
    st.markdown("<h1>Interaktivní Matice</h1>", unsafe_allow_html=True)
    st.markdown('<p style="color:#8A8A8A; font-size:13px; margin-top:-20px; margin-bottom:24px;">Premodern Metagame · Cross-selection Matrix · Scale centered at 50%</p>', unsafe_allow_html=True)
    
    # --- HORIZONTAL FILTER BAR ---
    f1, f2, f3 = st.columns([3, 1, 1])
    with f1:
        selected_decks = st.multiselect(
            "SELECTED DECKS", 
            all_archetypes, 
            default=all_archetypes[:8]
        )
    with f2:
        min_games = st.slider("MIN GAMES", 0, 50, 5)
    with f3:
        sort_by = st.selectbox("SORT BY", ["Alphabet", "Win Rate"])

    if not selected_decks:
        st.warning("Prosím vyberte alespoň jeden balík.")
        return

    # Data Processing
    if sort_by == "Win Rate":
        # Sort decks by their average winrate in the selection
        stats = []
        for d in selected_decks:
            wr_list = [matrix_dict.get(d, {}).get(o, {}).get("win_rate", 0.5) for o in selected_decks]
            stats.append((d, sum(wr_list)/len(wr_list)))
        selected_decks = [x[0] for x in sorted(stats, key=lambda x: x[1], reverse=True)]

    hm_data = []
    hover_data = []
    for arch1 in selected_decks:
        row = []
        hover_row = []
        for arch2 in selected_decks:
            cell = matrix_dict.get(arch1, {}).get(arch2, {})
            total = cell.get("total_matches", 0)
            wr = cell.get("win_rate", 0.5)
            
            if total >= min_games:
                row.append(wr)
                hover_row.append(f"WR: {wr:.1%}<br>Zápas: {cell['wins']}W - {cell['losses']}L<br>Hry: {total}")
            else:
                row.append(None)
                hover_row.append("Nedostatek dat")
        hm_data.append(row)
        hover_data.append(hover_row)

    # --- HEATMAP ---
    fig = px.imshow(
        hm_data,
        x=selected_decks,
        y=selected_decks,
        # Refined pastel diverging scale
        color_continuous_scale=[
            [0, "#FFB3BA"],     # Pastel Red
            [0.5, "#F1F2F6"],   # Off-white/Gray
            [1, "#BAFFC9"]      # Pastel Green
        ],
        labels=dict(color="Win Rate"),
        zmin=0.35, zmax=0.65, # Focused scale for better contrast
        text_auto='.1%',
        aspect="auto"
    )
    
    fig.update_layout(
        height=700,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color=THEME["text"],
        margin=dict(l=0, r=0, t=40, b=0),
    )
    
    # Custom hover template
    fig.update_traces(
        hovertemplate="<b>%{y} vs %{x}</b><br>%{customdata}<extra></extra>",
        customdata=hover_data
    )
    
    st.plotly_chart(fig, use_container_width=True)
    st.info("💡 Matice je nejčitelnější pro 2-10 balíků. Pro hlubší analýzu jednoho balíku použijte kartu 'Analýza Balíku'.")
