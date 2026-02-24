import streamlit as st
import pandas as pd
import plotly.express as px
from src.analytics import get_period_comparison, wilson_score_interval
from src.ui import THEME, style_winrate, html_deck_table

def _style(df, col):
    try:
        return df.style.map(style_winrate, subset=[col])
    except AttributeError:
        return df.style.applymap(style_winrate, subset=[col])

def show_meta_overview(matrix_dict, all_archetypes, records_data, data_dir, timeframes, tiers_dict=None, show_tier_filter=True):
    if tiers_dict is None: tiers_dict = {}
    st.markdown("<h1>Meta Overview</h1>", unsafe_allow_html=True)
    st.markdown(
        '<p style="color:#8A8A8A; font-size:13px; margin-top:-16px; margin-bottom:12px;">'
        'Premodern Metagame · Matchup Matrix + Historical Trends · Data: Duress Crew</p>',
        unsafe_allow_html=True
    )

    available_tiers = sorted(list(set(tiers_dict.values()))) if tiers_dict else []
    default_tiers = ["Tier 1"] if "Tier 1" in available_tiers else available_tiers
    selected_tiers = []
    
    if available_tiers and show_tier_filter:
        st.markdown("###### Filter Metagame")
        selected_tiers = st.multiselect(
            "Select Tiers",
            available_tiers,
            default=default_tiers,
            key="overview_global_tier_select",
            label_visibility="collapsed"
        )
        if selected_tiers and tiers_dict:
            all_archetypes = [a for a in all_archetypes if tiers_dict.get(a) in selected_tiers]
        if records_data:
            records_data = [r for r in records_data if r.get("archetype") in all_archetypes]
            
    if not all_archetypes:
        all_archetypes = ["None"]
        
    tier1_decks = [a for a in all_archetypes if tiers_dict.get(a) == "Tier 1"]
    default_trend_decks = tier1_decks if tier1_decks else all_archetypes[:5]

    def _draw_trend_chart(selected_decks_list):
        st.subheader("Win Rate Trends")
        

        
        with st.spinner("Loading historical data..."):
            pivot_wr, games_df = get_period_comparison(data_dir, timeframes)

            if pivot_wr.empty:
                st.error("Could not load trend data.")
                return

            valid_trend_decks = [d for d in selected_decks_list if d in pivot_wr.index]

            if not valid_trend_decks:
                st.warning("No selected decks have enough historical data.")
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
                height=420, hovermode="closest",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color=THEME["text"],
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=0, r=0, t=20, b=0),
            )
            fig_t.update_yaxes(tickformat=".0%", range=[0.3, 0.7])
            st.plotly_chart(fig_t, use_container_width=True)

    tab_stats, tab_matchups = st.tabs(["Metagame Stats", "Matchup Matrix"])

    # ─── TAB 1: METAGAME STATS ───────────────────────────────────────────────
    with tab_stats:
        if records_data:
            df_rec = (
                pd.DataFrame(records_data)
                .rename(columns={"archetype": "Deck", "win_rate": "Win Rate", "total_matches": "Games"})
                .sort_values("Win Rate", ascending=False)
            )

            c_top, c_bot = st.columns(2)
            
            # Filter for meaningful sample size (e.g. >= 20 games) 
            df_reliable = df_rec[df_rec["Games"] >= 20]
            if len(df_reliable) < 5:
                # fallback to taking the top N by games if nothing hit 20
                df_reliable = df_rec.sort_values("Games", ascending=False).head(10).sort_values("Win Rate", ascending=False)
                
            with c_top:
                st.subheader("Best 5 Win Rate Decks")
                d = df_reliable.head(5)[["Deck", "Win Rate", "Games"]].copy()
                d["Win Rate"] = d["Win Rate"].map(lambda x: f"{x:.1%}")
                st.markdown(html_deck_table(d, ["Deck", "Win Rate", "Games"], data_dir=data_dir), unsafe_allow_html=True)

            with c_bot:
                st.subheader("Worst 5 Win Rate Decks")
                d = df_reliable.tail(5).sort_values("Win Rate", ascending=True)[["Deck", "Win Rate", "Games"]].copy()
                d["Win Rate"] = d["Win Rate"].map(lambda x: f"{x:.1%}")
                st.markdown(html_deck_table(d, ["Deck", "Win Rate", "Games"], data_dir=data_dir), unsafe_allow_html=True)

            st.markdown('<div style="margin: 8px 0 12px 0; border-top: 1px solid #222222;"></div>', unsafe_allow_html=True)

            st.subheader("All Decks (Overall Metagame)")
            d_all = df_rec.copy()
            
            def _get_interval(row):
                # df_rec has columns: wins (not renamed), Games (was total_matches)
                w = row.get("wins", 0)
                t = row.get("Games", 0)
                if t == 0: return "n/a"
                l, u = wilson_score_interval(w, t)
                return f"{l:.1%} – {u:.1%}"
                
            d_all["Confidence Interval"] = d_all.apply(_get_interval, axis=1)
            d_all = d_all[["Deck", "Win Rate", "Confidence Interval", "Games"]].rename(columns={"Games": "Sample Size"})
            d_all["Win Rate"] = d_all["Win Rate"].map(lambda x: f"{x:.1%}")
            
            st.markdown(html_deck_table(d_all, ["Deck", "Win Rate", "Confidence Interval", "Sample Size"], data_dir=data_dir), unsafe_allow_html=True)

            st.markdown('<div style="margin: 8px 0 12px 0; border-top: 1px solid #222222;"></div>', unsafe_allow_html=True)
            selected_trend_decks_stats = st.multiselect(
                "Select Decks for Trends",
                all_archetypes,
                default=default_trend_decks,
                key="stats_trend_decks",
            )
            if selected_trend_decks_stats:
                _draw_trend_chart(selected_trend_decks_stats)

    # ─── TAB 2: MATCHUP MATRIX ───────────────────────────────────────────────
    with tab_matchups:
        default_decks = tier1_decks if tier1_decks else all_archetypes[:15]

        # ── SHARED DECK SELECTOR ─────────────────────────────────────────
        f1, f2, f3 = st.columns([3, 1, 1])
        with f1:
            selected_decks = st.multiselect(
                "Select Decks",
                all_archetypes, # Can still pick any
                default=default_decks,
                key="overview_deck_select",
            )
        with f2:
            min_games = st.slider("Min Games (matrix)", 0, 50, 5, key="overview_min_games")
        with f3:
            sort_by = st.selectbox("Sort By", ["Win Rate", "Alphabet"], key="overview_sort")

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

        if not decks_for_matrix:
            st.info("No decks match the current filters.")
            st.markdown('<div style="margin: 8px 0 12px 0; border-top: 1px solid #222222;"></div>', unsafe_allow_html=True)
            _draw_trend_chart(selected_decks)
            return

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

        st.markdown('<div style="margin: 8px 0 12px 0; border-top: 1px solid #222222;"></div>', unsafe_allow_html=True)

        # ─── WIN RATE TRENDS ─────────────────────────────────────────────
        _draw_trend_chart(selected_decks)

