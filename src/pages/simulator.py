import streamlit as st
import pandas as pd
import plotly.express as px
from src.analytics import calculate_expected_winrate
from src.ui import THEME, style_winrate, html_deck_table

def show_simulator(matrix_dict, all_archetypes, records_data):
    st.markdown('<h1 style="font-size: 24px;">Tournament Simulator</h1>', unsafe_allow_html=True)

    st.subheader("1. Field Composition")
    st.caption("Set expected share (%) for each deck. Remaining % auto-assigned to Unknown/Other.")

    top_8 = [r["archetype"] for r in sorted(records_data, key=lambda x: x.get("total_matches", 0), reverse=True)[:8]]

    meta_shares = {}
    total_assigned = 0

    cols = st.columns(4)
    for i, deck in enumerate(top_8):
        with cols[i % 4]:
            share = st.slider(f"{deck}", 0, 100, 10 if i < 3 else 5, key=f"sim_sld_{deck}")
            meta_shares[deck] = share / 100
            total_assigned += share

    remaining = max(0, 100 - total_assigned)
    if total_assigned > 100:
        st.warning(f"Total exceeds 100% by {total_assigned - 100}%. Results will be normalized.")
    else:
        st.info(f"Other Decks: **{remaining}%**")

    meta_shares["Other Decks"] = remaining / 100

    if st.button("Calculate Projected EV", type="primary"):
        with st.spinner("Simulating..."):
            evs = calculate_expected_winrate(meta_shares, matrix_dict, all_archetypes)
            ev_df = pd.DataFrame(list(evs.items()), columns=["Deck", "Projected Win Rate"])
            ev_df = ev_df.sort_values("Projected Win Rate", ascending=False).reset_index(drop=True)
            ev_df["#"] = ev_df.index + 1

            st.divider()

            res_c1, res_c2 = st.columns([1, 1])
            with res_c1:
                st.markdown("<h3>Best Deck for the Field</h3>", unsafe_allow_html=True)
                d = ev_df[["#", "Deck", "Projected Win Rate"]].head(10).copy()
                d["Projected Win Rate"] = d["Projected Win Rate"].map(lambda x: f"{x:.1%}")
                st.markdown(html_deck_table(d, ["#", "Deck", "Projected Win Rate"], wr_col="Projected Win Rate"), unsafe_allow_html=True)

            with res_c2:
                st.markdown("<h3>Visual Ranking</h3>", unsafe_allow_html=True)
                fig = px.bar(
                    ev_df.head(10),
                    x="Deck", y="Projected Win Rate",
                    color="Projected Win Rate",
                    color_continuous_scale=[[0, THEME["danger"]], [0.5, THEME["border"]], [1, THEME["success"]]],
                    range_color=[0.4, 0.6],
                    template="plotly_dark"
                )
                fig.update_layout(
                    showlegend=False, height=350,
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=0, r=0, t=20, b=0),
                    font_color=THEME["text"]
                )
                fig.update_yaxes(tickformat=".0%")
                st.plotly_chart(fig, use_container_width=True)

    st.caption("Note: projections based on historical matchup data. Real results may vary based on play skill and metagame tech.")
