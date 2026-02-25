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
    st.markdown('<h1 style="font-size: 24px;">Meta Overview</h1>', unsafe_allow_html=True)

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
        
    # Find Tier 1 + Tier 2 decks dynamically to use as default selections
    tier1_decks = [deck for deck, tier in tiers_dict.items() if tier in ("Tier 1", "Tier 2")] if tiers_dict else []
    
    if tier1_decks:
        # Use all tier 1 & 2 decks + top 5 by win rate
        custom_defaults = [d for d in tier1_decks if d in all_archetypes]
        if records_data:
            top_wr = sorted(records_data, key=lambda x: x.get("win_rate", 0), reverse=True)
            added = 0
            for r in top_wr:
                d = r.get("archetype")
                if d and d in all_archetypes and d not in custom_defaults:
                    custom_defaults.append(d)
                    added += 1
                if added >= 5:
                    break
    else:
        # Fallback to User's preferred default decks if tiers data is missing
        user_preferred = ["Replenish", "Goblins", "Landstill", "Burn", "Stiflenought"]
        custom_defaults = [d for d in user_preferred if d in all_archetypes]
        
    if not custom_defaults:
        custom_defaults = all_archetypes[:15]

    def _draw_trend_chart(selected_decks_list, key_suffix=""):
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
                showlegend=False,
                margin=dict(l=0, r=0, t=20, b=0),
                xaxis_title="",
            )
            fig_t.update_yaxes(tickformat=".0%", range=[0.35, 0.65])
            # Add deck names at the last data point of each line
            last_period = existing[-1] if existing else None
            if last_period:
                for deck in valid_trend_decks:
                    wr_val = pivot_wr.loc[deck].get(last_period)
                    if pd.notna(wr_val):
                        fig_t.add_annotation(
                            x=last_period, y=wr_val,
                            text=deck, showarrow=False,
                            xanchor="left", yanchor="middle",
                            xshift=8,
                            font=dict(size=10, family="IBM Plex Mono"),
                        )
            
            # Horizontally shrink the chart by placing it in a centered column
            _, chart_col, _ = st.columns([0.1, 0.8, 0.1])
            with chart_col:
                st.plotly_chart(fig_t, use_container_width=True, key=f"trend_chart_{key_suffix}")

    tab_stats, tab_matchups = st.tabs(["Metagame Stats", "Matchup Matrix"])

    # ─── TAB 1: METAGAME STATS ───────────────────────────────────────────────
    with tab_stats:
        if records_data:
            df_rec = (
                pd.DataFrame(records_data)
                .rename(columns={"archetype": "Deck", "win_rate": "Win Rate", "total_matches": "Games"})
                .sort_values("Win Rate", ascending=False)
            )
            df_rec = df_rec[df_rec["Deck"] != "Unknown"]

            # ─── Compute meta shares early (used by scatter + table) ─────────
            matchups_matrix = matrix_dict.get("matrix", matrix_dict) 
            meta_shares     = matrix_dict.get("meta_shares", {})
            def _get_share_num(deck):
                s = meta_shares.get(deck)
                if s is None: s = meta_shares.get(deck.upper())
                return s if s is not None else 0.0

            df_rec["Meta Share (Num)"] = df_rec["Deck"].map(_get_share_num)
            df_rec["Win Rate (Num)"]   = df_rec["Win Rate"]

            # --- SCATTER PLOT: Metagame Share vs Win Rate ---
            st.subheader("Win Rate vs Metagame Share")
            scatter_df = df_rec[(df_rec["Meta Share (Num)"] > 0) & (df_rec["Games"] >= 20)].copy()

            if scatter_df.empty:
                st.info("Meta share data not available for this timeframe.")
            else:
                from src.ui import get_circular_icon_b64

                max_share = scatter_df["Meta Share (Num)"].max() or 0.1
                x_max = max_share * 1.18

                y_max = max(0.65, scatter_df["Win Rate (Num)"].max() + 0.03)
                y_min = min(0.35, scatter_df["Win Rate (Num)"].min() - 0.03)
                y_range = y_max - y_min
                x_range = x_max

                scatter_df["tooltip"] = scatter_df.apply(
                    lambda r: f"<b>{r['Deck']}</b><br><br>Meta Share: {r['Meta Share (Num)']:.1%}<br>Win Rate: {r['Win Rate (Num)']:.1%}<br>Games: {r['Games']}",
                    axis=1
                )

                fig_s = px.scatter(
                    scatter_df,
                    x="Meta Share (Num)",
                    y="Win Rate (Num)",
                    hover_name="tooltip",
                    template="plotly_dark"
                )
                fig_s.update_traces(hovertemplate="%{hovertext}<extra></extra>")
                fig_s.add_hline(y=0.5, line_dash="dash", line_color=THEME["faint"])

                icon_sizex = x_range * 0.095
                icon_sizey = y_range * 0.115

                for _, row in scatter_df.iterrows():
                    deck  = row["Deck"]
                    x_val = row["Meta Share (Num)"]
                    y_val = row["Win Rate (Num)"]
                    b64 = get_circular_icon_b64(deck, data_dir)
                    if b64:
                        fig_s.add_layout_image(dict(
                            source=f"data:image/png;base64,{b64}",
                            xref="x", yref="y",
                            x=x_val, y=y_val,
                            sizex=icon_sizex, sizey=icon_sizey,
                            xanchor="center", yanchor="middle",
                            sizing="contain", layer="above"
                        ))
                    else:
                        fig_s.add_annotation(
                            x=x_val, y=y_val,
                            text=deck, showarrow=False,
                            font=dict(size=9, color=THEME["muted"]),
                            xanchor="center", yanchor="bottom", yshift=8
                        )

                fig_s.update_traces(
                    marker=dict(color="rgba(255,255,255,0.15)", size=22,
                                line=dict(color="rgba(255,255,255,0.3)", width=1))
                )
                fig_s.update_layout(
                    height=380,
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font_color=THEME["text"],
                    margin=dict(l=20, r=20, t=30, b=20),
                    xaxis_title="Metagame Share",
                    yaxis_title="Win Rate",
                    xaxis=dict(tickformat=".0%", range=[0, x_max]),
                    yaxis=dict(tickformat=".0%", range=[y_min, y_max]),
                    showlegend=False,
                )
                st.plotly_chart(fig_s, use_container_width=True, key="scatter_meta_winrate")

            st.markdown('<div style="margin: 8px 0 12px 0; border-top: 1px solid #222222;"></div>', unsafe_allow_html=True)

            c_top, c_bot = st.columns(2)
            
            # Filter for meaningful sample size (e.g. >= 20 games) 
            df_reliable = df_rec[df_rec["Games"] >= 20]
            if len(df_reliable) < 5:
                df_reliable = df_rec.sort_values("Games", ascending=False).head(10).sort_values("Win Rate", ascending=False)
                
            with c_top:
                st.markdown("<h3>Best 5 Decks <span title='Decks with fewer than 20 games are excluded to ensure statistical reliability.' style='cursor:help; font-size:14px; color:#8A8A8A; opacity:0.8;'>&#9432;</span></h3>", unsafe_allow_html=True)
                d = df_reliable.head(5)[["Deck", "Win Rate", "Meta Share (Num)", "Games"]].copy()
                d["Win Rate"] = d["Win Rate"].map(lambda x: f"{x:.1%}")
                d["Meta Share"] = d["Meta Share (Num)"].apply(lambda s: f"{s:.1%}" if s > 0 else "n/a")
                st.markdown(html_deck_table(d, ["Deck", "Win Rate", "Meta Share", "Games"], data_dir=data_dir), unsafe_allow_html=True)

            with c_bot:
                st.markdown("<h3>Worst 5 Decks <span title='Decks with fewer than 20 games are excluded to ensure statistical reliability.' style='cursor:help; font-size:14px; color:#8A8A8A; opacity:0.8;'>&#9432;</span></h3>", unsafe_allow_html=True)
                d = df_reliable.tail(5).sort_values("Win Rate", ascending=True)[["Deck", "Win Rate", "Meta Share (Num)", "Games"]].copy()
                d["Win Rate"] = d["Win Rate"].map(lambda x: f"{x:.1%}")
                d["Meta Share"] = d["Meta Share (Num)"].apply(lambda s: f"{s:.1%}" if s > 0 else "n/a")
                st.markdown(html_deck_table(d, ["Deck", "Win Rate", "Meta Share", "Games"], data_dir=data_dir), unsafe_allow_html=True)

            st.markdown('<div style="margin: 8px 0 12px 0; border-top: 1px solid #222222;"></div>', unsafe_allow_html=True)

            st.subheader("All Decks by Win Rate")
            d_all = df_rec.copy()
            d_all["Meta Share"] = d_all["Meta Share (Num)"].apply(lambda s: f"{s:.1%}" if s > 0 else "n/a")

            def _get_interval(row):
                w = row.get("wins", 0)
                t = row.get("Games", 0)
                if t == 0: return "n/a"
                l, u = wilson_score_interval(w, t)
                return f"{l:.1%} – {u:.1%}"
                
            d_all["Confidence Interval"] = d_all.apply(_get_interval, axis=1)
            d_table = d_all[["Deck", "Win Rate (Num)", "Meta Share", "Confidence Interval", "Games"]].copy()
            d_table = d_table.rename(columns={"Games": "Sample Size", "Win Rate (Num)": "Win Rate"})
            d_table["Win Rate"] = d_table["Win Rate"].map(lambda x: f"{x:.1%}")
            
            st.markdown(html_deck_table(d_table, ["Deck", "Win Rate", "Meta Share", "Confidence Interval", "Sample Size"], data_dir=data_dir), unsafe_allow_html=True)

            st.markdown('<div style="margin: 8px 0 12px 0; border-top: 1px solid #222222;"></div>', unsafe_allow_html=True)
            selected_trend_decks_stats = st.multiselect(
                "Select Decks for Trends",
                all_archetypes,
                default=custom_defaults,
                key="stats_trend_decks",
            )
            if selected_trend_decks_stats:
                _draw_trend_chart(selected_trend_decks_stats, key_suffix="stats")


    # ─── TAB 2: MATCHUP MATRIX ───────────────────────────────────────────────
    with tab_matchups:
        # ── SHARED DECK SELECTOR ─────────────────────────────────────────
        f1, f2, f3 = st.columns([3, 1, 1])
        with f1:
            selected_decks = st.multiselect(
                "Select Decks",
                all_archetypes, # Can still pick any
                default=custom_defaults,
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
                (d, sum(matchups_matrix.get(d, {}).get(o, {}).get("win_rate", 0.5) for o in decks_for_matrix) / len(decks_for_matrix))
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
                cell  = matchups_matrix.get(arch1, {}).get(arch2, {})
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
        _draw_trend_chart(selected_decks, key_suffix="matrix")

