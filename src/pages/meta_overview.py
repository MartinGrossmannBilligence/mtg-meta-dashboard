import streamlit as st
import pandas as pd
import plotly.express as px
from src.analytics import get_period_comparison
from src.ui import THEME, style_winrate

def _style(df, col):
    try:
        return df.style.map(style_winrate, subset=[col])
    except AttributeError:
        return df.style.applymap(style_winrate, subset=[col])

def show_meta_overview(matrix_dict, all_archetypes, records_data, data_dir, timeframes):
    st.markdown("<h1>Meta Overview</h1>", unsafe_allow_html=True)
    st.markdown(
        '<p style="color:#8A8A8A; font-size:13px; margin-top:-20px; margin-bottom:24px;">'
        'Premodern Metagame · Matchup Matrix + Historical Trends · Data: Duress Crew</p>',
        unsafe_allow_html=True
    )

    # ── OVERALL TOP 5 / BOTTOM 5 from records data ───────────────────────────
    if records_data:
        df_rec = (
            pd.DataFrame(records_data)
            .rename(columns={"archetype": "Deck", "win_rate": "Win Rate", "total_matches": "Games"})
            .sort_values("Win Rate", ascending=False)
        )

        c_top, c_bot = st.columns(2)
        with c_top:
            st.subheader("Best 5 Win Rate Decks")
            d = df_rec.head(5)[["Deck", "Win Rate", "Games"]].copy()
            d["Win Rate"] = d["Win Rate"].map(lambda x: f"{x:.1%}")
            st.dataframe(_style(d, "Win Rate"), use_container_width=True, hide_index=True)

        with c_bot:
            st.subheader("Worst 5 Win Rate Decks")
            d = df_rec.tail(5)[["Deck", "Win Rate", "Games"]].copy()
            d["Win Rate"] = d["Win Rate"].map(lambda x: f"{x:.1%}")
            st.dataframe(_style(d, "Win Rate"), use_container_width=True, hide_index=True)

        st.divider()

        st.subheader("All Decks (Overall Metagame)")
        d_all = df_rec[["Deck", "Win Rate", "Games"]].copy()
        d_all["Win Rate"] = d_all["Win Rate"].map(lambda x: f"{x:.1%}")
        st.dataframe(_style(d_all, "Win Rate"), use_container_width=True, hide_index=True)

        st.divider()

    # ── SHARED DECK SELECTOR (drives both tabs) ───────────────────────────────
    f1, f2, f3 = st.columns([3, 1, 1])
    with f1:
        selected_decks = st.multiselect(
            "SELECTED DECKS",
            all_archetypes,
            default=all_archetypes[:10],
            key="overview_deck_select",
        )
    with f2:
        min_games = st.slider("MIN GAMES (matrix)", 0, 50, 5, key="overview_min_games")
    with f3:
        sort_by = st.selectbox("SORT BY", ["Win Rate", "Alphabet"], key="overview_sort")

    if not selected_decks:
        st.warning("Select at least one deck.")
        return

    # ─── MATCHUP MATRIX ───────────────────────────────────────────────
    st.subheader("Matchup Matrix")
    decks_for_matrix = list(selected_decks)
    if sort_by == "Win Rate":
        stats = [
            (d, sum(matrix_dict.get(d, {}).get(o, {}).get("win_rate", 0.5) for o in decks_for_matrix) / len(decks_for_matrix))
            for d in decks_for_matrix
        ]
        decks_for_matrix = [x[0] for x in sorted(stats, key=lambda x: x[1], reverse=True)]

    hm_data, hover_data = [], []
    for arch1 in decks_for_matrix:
        row, hover_row = [], []
        for arch2 in decks_for_matrix:
            cell  = matrix_dict.get(arch1, {}).get(arch2, {})
            total = cell.get("total_matches", 0)
            wr    = cell.get("win_rate", 0.5)
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
        x=decks_for_matrix, y=decks_for_matrix,
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
    st.caption("Scale centered at 50% (35%–65%). Blank cells = insufficient data.")

    st.divider()

    # ─── WIN RATE TRENDS (same deck selection) ────────────────────────
    st.subheader("Win Rate Trends")
    with st.spinner("Loading historical data..."):
        pivot_wr, games_df = get_period_comparison(data_dir, timeframes)

        if pivot_wr.empty:
            st.error("Could not load trend data.")
            return

        # Filter selected_decks to those that exist in pivot_wr
        valid_trend_decks = [d for d in selected_decks if d in pivot_wr.index]

        if not valid_trend_decks:
            st.warning("No selected decks have enough historical data. Adjust the SELECTED DECKS filter above.")
            return

        ordered_periods = list(timeframes.keys())
        existing = [p for p in ordered_periods if p in pivot_wr.columns]
        trend_df = pivot_wr.loc[valid_trend_decks][existing].T

        fig_t = px.line(
            trend_df, markers=True,
            labels={"value": "Win Rate", "index": "Period"},
            template="plotly_dark",
            color_discrete_sequence=px.colors.qualitative.Safe,
        )
        fig_t.add_hline(y=0.5, line_dash="dash", line_color=THEME["faint"])
        fig_t.update_layout(
            height=420, hovermode="x unified",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color=THEME["text"],
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=0, r=0, t=20, b=0),
        )
        fig_t.update_yaxes(tickformat=".0%", range=[0.3, 0.7])
        st.plotly_chart(fig_t, use_container_width=True)

        raw = pivot_wr.loc[valid_trend_decks][existing].fillna("—")
        st.dataframe(_style(raw, None) if False else raw, use_container_width=True)
        st.caption("'—' = insufficient data for that period. Deck selection mirrors the filter above.")
