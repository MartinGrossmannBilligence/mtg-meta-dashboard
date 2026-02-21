import streamlit as st
import pandas as pd
import plotly.express as px
from src.analytics import calculate_expected_winrate
from src.ui import THEME, style_winrate

def show_simulator(matrix_dict, all_archetypes, records_data):
    st.markdown("<h1>TOURNAMENT SIMULATOR</h1>", unsafe_allow_html=True)
    st.markdown('<p style="color:#8A8A8A; font-size:13px; margin-top:-20px; margin-bottom:24px;">META PROJECTIONS · SENSITIVITY ANALYSIS · AUTO-NORMALIZATION</p>', unsafe_allow_html=True)
    
    # --- PRESETS ---
    with st.expander("🛠️ PRESETS"):
        preset = st.radio("SELECT PRESET", ["Custom", "Last 90d", "Online Heavy", "Paper Heavy"], horizontal=True)
        # Note: In a real app, these would load specific weights. For now, we'll just show the concept.
        if preset != "Vlastní":
            st.info(f"Preset '{preset}' byl aplikován (demo).")

    st.subheader("1. Složení turnajového pole")
    st.caption("Zadejte očekávané procentuální zastoupení hlavních balíků. Celkový součet se automaticky dopočítá do 100% (Unknown).")
    
    # Get top 8 decks by popularity for quick sliders
    top_8 = [r["archetype"] for r in sorted(records_data, key=lambda x: x.get("total_matches", 0), reverse=True)[:8]]
    
    meta_shares = {}
    total_assigned = 0
    
    cols = st.columns(4)
    for i, deck in enumerate(top_8):
        with cols[i % 4]:
            share = st.slider(f"{deck} (%)", 0, 100, 10 if i < 3 else 5, key=f"sim_sld_{deck}")
            meta_shares[deck] = share / 100
            total_assigned += share
            
    # Auto-normalization / Unknown
    remaining = max(0, 100 - total_assigned)
    st.info(f"Ostatní / Neznámé (Unknown): **{remaining}%**")
    if total_assigned > 100:
        st.warning("⚠️ Celkový podíl přesahuje 100%! Výsledky budou normalizovány.")
    
    # Add Unknown to shares for calculation
    meta_shares["Unknown"] = remaining / 100
    
    if st.button("🔥 Vypočítat očekávaný výkon (Projected EV)", type="primary"):
        with st.spinner("Simuluji tisíce her..."):
            evs = calculate_expected_winrate(meta_shares, matrix_dict, all_archetypes)
            ev_df = pd.DataFrame(list(evs.items()), columns=["Balík", "Očekávaná Win Rate"])
            ev_df = ev_df.sort_values("Očekávaná Win Rate", ascending=False).reset_index(drop=True)
            ev_df["Ranking"] = ev_df.index + 1
            
            st.divider()
            
            res_c1, res_c2 = st.columns([1, 1])
            with res_c1:
                st.subheader("🏆 Nejlepší volba pro pole")
                st.dataframe(
                    ev_df[["Ranking", "Balík", "Očekávaná Win Rate"]].head(10).style.applymap(style_winrate, subset=["Očekávaná Win Rate"]).format({"Očekávaná Win Rate": "{:.1%}"}),
                    use_container_width=True, hide_index=True
                )
            
            with res_c2:
                st.subheader("Grafické srovnání")
                fig = px.bar(
                    ev_df.head(10), 
                    x="Balík", y="Očekávaná Win Rate",
                    color="Očekávaná Win Rate",
                    color_continuous_scale=[[0, THEME["danger"]], [0.5, THEME["border"]], [1, THEME["success"]]],
                    range_color=[0.4, 0.6],
                    template="plotly_dark"
                )
                fig.update_layout(
                    showlegend=False,
                    height=350,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=0, r=0, t=20, b=0),
                    font_color=THEME["text"]
                )
                st.plotly_chart(fig, use_container_width=True)

    st.caption("Pamatujte: Simulace vychází z historických dat. Neočekávané technické inovace (tech) mohou reálný výsledek ovlivnit.")
