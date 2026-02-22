import streamlit as st
import pandas as pd
import plotly.express as px
from src.analytics import get_period_comparison
from src.ui import THEME, style_winrate

def show_meta_overview(matrix_dict, all_archetypes, data_dir, timeframes):
    st.markdown("<h1>Meta Overview</h1>", unsafe_allow_html=True)
    st.markdown('<p style="color:#8A8A8A; font-size:13px; margin-top:-20px; margin-bottom:24px;">Premodern Metagame · Matchup Matrix + Historical Trends · Data: Duress Crew</p>', unsafe_allow_html=True)

    tab_matrix, tab_trends = st.tabs(["Matchup Matrix", "Win Rate Trends"])

    # ─── TAB 1: MATCHUP MATRIX ──────────────────────────────────────────────
    with tab_matrix:
        f1, f2, f3 = st.columns([3, 1, 1])
        with f1:
            selected_decks = st.multiselect(
                "SELECTED DECKS",
                all_archetypes,
                default=all_archetypes[:10]
            )
        with f2:
            min_games = st.slider("MIN GAMES", 0, 50, 5)
        with f3:
            sort_by = st.selectbox("SORT BY", ["Alphabet", "Win Rate"])

        if not selected_decks:
            st.warning("Select at least one deck.")
        else:
            if sort_by == "Win Rate":
                stats = [(d, sum(matrix_dict.get(d, {}).get(o, {}).get("win_rate", 0.5) for o in selected_decks) / len(selected_decks)) for d in selected_decks]
                selected_decks = [x[0] for x in sorted(stats, key=lambda x: x[1], reverse=True)]

            hm_data, hover_data = [], []
            for arch1 in selected_decks:
                row, hover_row = [], []
                for arch2 in selected_decks:
                    cell = matrix_dict.get(arch1, {}).get(arch2, {})
                    total = cell.get("total_matches", 0)
                    wr = cell.get("win_rate", 0.5)
                    if total >= min_games:
                        row.append(wr)
                        hover_row.append(f"WR: {wr:.1%}<br>{cell.get('wins',0)}W – {cell.get('losses',0)}L<br>n={total}")
                    else:
                        row.append(None)
                        hover_row.append("Insufficient data")
                hm_data.append(row)
                hover_data.append(hover_row)

            fig = px.imshow(
                hm_data,
                x=selected_decks, y=selected_decks,
                color_continuous_scale=[[0, "#C76B6B"], [0.5, "#222222"], [1, "#6BC78E"]],
                zmin=0.35, zmax=0.65,
                text_auto=".1%",
                aspect="auto",
            )
            fig.update_layout(
                height=700,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color=THEME["text"],
                margin=dict(l=0, r=0, t=40, b=0),
            )
            fig.update_traces(
                hovertemplate="<b>%{y} vs %{x}</b><br>%{customdata}<extra></extra>",
                customdata=hover_data,
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Scale: 35%–65% · Cells with insufficient data (< min games) are blank.")

    # ─── TAB 2: WIN RATE TRENDS ─────────────────────────────────────────────
    with tab_trends:
        with st.spinner("Loading historical data..."):
            pivot_wr, games_df = get_period_comparison(data_dir, timeframes)

        if pivot_wr.empty:
            st.error("Could not load trend data.")
            return

        min_games_trend = st.slider("Min total games (all periods)", 0, 500, 100)
        total_all = games_df.sum(axis=1)
        top_decks = total_all[total_all >= min_games_trend].index.tolist()

        if not top_decks:
            st.warning("No decks match the filter.")
            return

        selected_trend = st.multiselect("DECKS FOR COMPARISON", top_decks, default=top_decks[:6])
        if not selected_trend:
            st.info("Select at least one deck.")
            return

        ordered_periods = list(timeframes.keys())
        existing = [p for p in ordered_periods if p in pivot_wr.columns]
        trend_df = pivot_wr.loc[selected_trend][existing].T

        fig_t = px.line(trend_df, markers=True,
                        labels={"value": "Win Rate", "index": "Period"},
                        template="plotly_dark",
                        color_discrete_sequence=px.colors.qualitative.Safe)
        fig_t.add_hline(y=0.5, line_dash="dash", line_color=THEME["faint"])
        fig_t.update_layout(
            height=450, hovermode="x unified",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color=THEME["text"],
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=0, r=0, t=20, b=0),
        )
        fig_t.update_yaxes(tickformat=".0%", range=[0.3, 0.7])
        st.plotly_chart(fig_t, use_container_width=True)

        raw = pivot_wr.loc[selected_trend][existing].fillna("—")
        st.dataframe(raw.style.applymap(style_winrate), use_container_width=True)
        st.caption("'—' = insufficient data for that period.")
