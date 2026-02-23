import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.analytics import load_period_data, wilson_score_interval, calculate_polarity
from src.ui import THEME, style_winrate

def _quality_badge(games):
    if games >= 50: return "High"
    if games >= 20: return "Avg"
    return "Low"

def _style_wr_col(df, col="Win Rate"):
    """Safely apply win rate coloring compatible with both old and new pandas."""
    try:
        return df.style.map(style_winrate, subset=[col])
    except AttributeError:
        return df.style.applymap(style_winrate, subset=[col])

def show_analysis(matrix_dict, all_archetypes, records_data, data_dir, timeframes):
    st.markdown("<h1>Deck Analysis</h1>", unsafe_allow_html=True)
    st.markdown(
        '<p style="color:#8A8A8A; font-size:13px; margin-top:-16px; margin-bottom:12px;">'
        'Premodern Metagame · Data: Duress Crew · Individual Deck Deep-Dive</p>',
        unsafe_allow_html=True
    )

    # Preserve deck selection across timeframe changes
    try:
        default_deck = next(x for x in all_archetypes if "stiflenought" in x.lower() or "dreadnought" in x.lower())
    except StopIteration:
        default_deck = all_archetypes[0] if all_archetypes else ""

    saved_deck = st.session_state.get("analysis_saved_deck", default_deck)
    if saved_deck not in all_archetypes:
        saved_deck = default_deck

    try:
        current_idx = all_archetypes.index(saved_deck)
    except ValueError:
        current_idx = 0

    target_deck = st.selectbox(
        "Select Deck", 
        all_archetypes, 
        index=current_idx
    )
    st.session_state["analysis_saved_deck"] = target_deck

    row_data    = matrix_dict.get(target_deck, {})
    deck_record = next((r for r in records_data if r["archetype"] == target_deck), {})
    overall_wr  = deck_record.get("win_rate", 0)
    total_games = deck_record.get("total_matches", 0)

    # Matchup rows with confidence intervals
    prof_rows = []
    for other in all_archetypes:
        if other == target_deck:
            continue
        cell  = row_data.get(other, {})
        total = cell.get("total_matches", 0)
        if total > 0:
            wins = cell.get("wins", 0)
            wr   = cell.get("win_rate", 0.5)
            lo, hi = wilson_score_interval(wins, total)
            prof_rows.append({
                "Opponent": other,
                "WR":       wr,
                "95% CI":   f"{lo:.1%} – {hi:.1%}",
                "Record":   f"{wins}W – {cell.get('losses', 0)}L",
                "Games":    total,
                "Sample":   _quality_badge(total),
            })

    df_prof = pd.DataFrame(prof_rows).sort_values("WR", ascending=False) if prof_rows else pd.DataFrame()

    # Polarity percentile
    all_polarities = [calculate_polarity(a, matrix_dict, all_archetypes) for a in all_archetypes]
    polarity       = calculate_polarity(target_deck, matrix_dict, all_archetypes)
    pct_rank       = int(100 * sum(p <= polarity for p in all_polarities) / max(len(all_polarities), 1))
    pct_label      = (
        "high polarity — strong matchup spread (rock-paper-scissors)" if pct_rank > 66
        else "average polarity" if pct_rank > 33
        else "stable — consistent matchup profile across the field"
    )

    tab_stats, tab_decks = st.tabs(["Statistics", "Deck Lists"])

    with tab_stats:
        # --- KPI & DISTRIBUTION ROW (4 equal columns) ---
        c1, c2, c3, c_chart = st.columns(4)
    
        with c1:
            st.metric("Overall Win Rate", f"{overall_wr:.1%}")
        with c2:
            st.metric("Total Games", f"{total_games:,}")
        with c3:
            if not df_prof.empty:
                df_prof["Bracket"] = pd.cut(
                    df_prof["WR"],
                    bins=[0, 0.45, 0.55, 1.0],
                    labels=["Unfavoured (<45%)", "Even (45-55%)", "Favoured (>55%)"],
                )
                counts = df_prof["Bracket"].value_counts()
                bad_n  = int(counts.get("Unfavoured (<45%)", 0))
                even_n = int(counts.get("Even (45-55%)", 0))
                good_n = int(counts.get("Favoured (>55%)", 0))

                colored_text = (
                    f"<span style='color:{THEME['success']}'>{good_n}↑</span> "
                    f"<span style='color:{THEME['faint']}'>{even_n}~</span> "
                    f"<span style='color:{THEME['danger']}'>{bad_n}↓</span>"
                )
            
                # Using markdown instead of st.metric to allow HTML colors inside the value
                st.markdown(
                    f"""
                    <div data-testid="stMetric">
                        <div style="font-size:11px; color:#8A8A8A; margin-bottom:2px; text-transform:uppercase; letter-spacing:0.06em;">
                            Matchup Distribution <span title="{good_n} favoured (>55%) · {even_n} even (45–55%) · {bad_n} unfavoured (<45%)" style="cursor:help; font-size:12px; margin-left:4px; opacity:0.8;">&#9432;</span>
                        </div>
                        <div style="font-size: 1.8rem; font-weight: 500;">{colored_text}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        with c_chart:
            st.metric(
                "Polarity Index",
                f"{polarity * 100:.1f}%",
                help=f"Spread of matchup win rates. {pct_rank}th percentile — {pct_label}.",
            )

        st.markdown('<div style="margin: 8px 0 12px 0; border-top: 1px solid #222222;"></div>', unsafe_allow_html=True)

        # --- WIN RATE HISTORY ---
        st.subheader("Win Rate Trend")
    


        history_rows = []
        for period_label, period_key in timeframes.items():
            try:
                _, rdata = load_period_data(data_dir, period_key)
                rec = next((r for r in rdata if r["archetype"] == target_deck), None)
                if rec:
                    history_rows.append({
                        "Period":   period_label,
                        "Win Rate": rec["win_rate"],
                        "Games":    rec["total_matches"],
                    })
            except Exception:
                pass

        if history_rows:
            df_hist = pd.DataFrame(history_rows)

            def _wr_color(v):
                if v > 0.55: return THEME["success"]
                if v < 0.45: return THEME["danger"]
                if v < 0.50: return THEME["warning"]
                return THEME["text"]

            fig_hist = go.Figure()
            fig_hist.add_trace(go.Scatter(
                x=df_hist["Period"], y=df_hist["Win Rate"],
                mode="lines+markers+text",
                text=[f"{v:.1%}" for v in df_hist["Win Rate"]],
                textposition="top center",
                textfont=dict(
                    size=15,
                    color=[_wr_color(v) for v in df_hist["Win Rate"]],
                ),
                line=dict(color=THEME["border"], width=7),
                marker=dict(
                    size=10,
                    color=[_wr_color(v) for v in df_hist["Win Rate"]],
                    line=dict(width=0),
                ),
            ))
            fig_hist.add_hline(y=0.5, line_dash="dash", line_color=THEME["faint"], line_width=1)
            fig_hist.update_layout(
                height=200,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color=THEME["muted"],
                font_family="IBM Plex Mono",
                margin=dict(l=0, r=0, t=30, b=0),
                yaxis=dict(tickformat=".0%", range=[0.3, 0.7], tickfont=dict(size=12)),
                xaxis=dict(tickfont=dict(size=13)),
                xaxis_title="", yaxis_title="",
            )
            st.plotly_chart(fig_hist, use_container_width=True)

        st.markdown('<div style="margin: 8px 0 12px 0; border-top: 1px solid #222222;"></div>', unsafe_allow_html=True)

        # --- TOP 5 / WORST 5 ---
        col_best, col_worst = st.columns(2)

        def _table(df_slice):
            d = df_slice[["Opponent", "WR", "Games", "Record"]].copy()
            d = d.rename(columns={"WR": "Win Rate"})
            d["Win Rate"] = d["Win Rate"].map(lambda x: f"{x:.1%}")
            return _style_wr_col(d)

        with col_best:
            col_best.markdown("###### Best Matchups")
        
        # Split into reliable (>= 20 games) and unreliable (< 20 games)
        if not df_prof.empty:
            df_reliable = df_prof[df_prof["Games"] >= 20].sort_values("WR", ascending=False)
            df_unreliable = df_prof[df_prof["Games"] < 20].sort_values("WR", ascending=False)
            
            # Get top 5 best
            best_matchups = df_reliable.head(5)
            if len(best_matchups) < 5:
                needed = 5 - len(best_matchups)
                best_matchups = pd.concat([best_matchups, df_unreliable.head(needed)])
                
            # Get bottom 5 worst (sort ascending first)
            df_reliable_worst = df_reliable.sort_values("WR", ascending=True)
            df_unreliable_worst = df_unreliable.sort_values("WR", ascending=True)
            
            worst_matchups = df_reliable_worst.head(5)
            if len(worst_matchups) < 5:
                needed = 5 - len(worst_matchups)
                worst_matchups = pd.concat([worst_matchups, df_unreliable_worst.head(needed)])
        else:
            best_matchups = pd.DataFrame()
            worst_matchups = pd.DataFrame()

        if not best_matchups.empty:
            col_best.dataframe(_table(best_matchups), use_container_width=True, hide_index=True)

        col_worst.markdown("###### Worst Matchups")
        if not worst_matchups.empty:
            col_worst.dataframe(_table(worst_matchups), use_container_width=True, hide_index=True)

        st.markdown('<div style="margin: 8px 0 12px 0; border-top: 1px solid #222222;"></div>', unsafe_allow_html=True)

        # --- FULL MATCHUP TABLE ---
        st.subheader("All Matchups")
        if not df_prof.empty:
            df_display = df_prof[["Opponent", "WR", "95% CI", "Record", "Games", "Sample"]].copy()
            df_display = df_display.rename(columns={"WR": "Win Rate", "95% CI": "Confidence Interval", "Sample": "Sample Size"})
            df_display["Win Rate"] = df_display["Win Rate"].map(lambda x: f"{x:.1%}")
            st.dataframe(
                _style_wr_col(df_display),
                use_container_width=True, hide_index=True
            )



    with tab_decks:
        from src.mtgdecks_scraper import get_recent_top_decks, get_decklist
        decks = get_recent_top_decks(target_deck)
        if not decks:
            st.info("No recent decklists found matching the criteria (>=50 players, Top 8).")
        else:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("#### Recent Top Decklists")
            
            # Map mtgdecks color codes to hex codes for visual display
            color_map = {
                'W': '#F8F6D8', 'U': '#C1D8E9', 'B': '#BAB1AB', 
                'R': '#E49977', 'G': '#A3C095', 'C': '#CCCCCC'
            }
            
            import textwrap
            
            # Wrap in a styled container
            html_content = '<div style="background-color: #1A1A1A; border: 1px solid #2A2A2A; border-radius: 8px; padding: 16px;">'
            
            for i, d in enumerate(decks):
                # Get the actual cards for hover
                cards = get_decklist(d['url'])
                if cards:
                    hover_text = " | ".join([f"{c['qty']}x {c['name']}" for c in cards])
                else:
                    hover_text = "Preview not available"
                
                # Render colors as little dots
                color_dots = ""
                for c in d.get("colors", []):
                    color_hex = color_map.get(c, '#888')
                    color_dots += f'<span style="display:inline-block; width:10px; height:10px; border-radius:50%; background-color:{color_hex}; margin-right:3px; border:1px solid rgba(255,255,255,0.2);"></span>'
                
                # Render spiciness badge if > 0
                spice = d.get('spice', 0)
                spice_badge = ""
                if spice > 0:
                    spice_color = "#E49977" if spice > 50 else "#F59F00" if spice > 20 else "#8A8A8A"
                    spice_badge = f'<span style="margin-left:8px; font-size:10px; color:{spice_color}; border:1px solid {spice_color}40; padding:1px 6px; border-radius:10px; background:rgba(0,0,0,0.2);">🌶️ Spice: {spice}%</span>'
                
                border_bottom = 'border-bottom: 1px solid #2A2A2A;' if i < len(decks) - 1 else ''
                margin_bottom = 'margin-bottom: 12px; padding-bottom: 12px;' if i < len(decks) - 1 else ''
                
                html_block = f"""
                <div style="{margin_bottom} {border_bottom}" title="{hover_text}">
                    <div style="display:flex; align-items:center; margin-bottom: 2px;">
                        <strong style="margin-right:8px; font-size:15px; color:#E0E0E0;">{d['rank']}</strong> 
                        <a href="{d['url']}" target="_blank" style="color:#6BC78E; text-decoration:none; margin-right:10px; font-size:15px;">{d['player']}</a>
                        {color_dots}
                        {spice_badge}
                    </div>
                    <div style="font-size:12px; color:#8A8A8A; display:flex; gap:10px;">
                        <span>🗓️ {d['date']}</span>
                        <span>🏆 {d['event']}</span>
                        <span>👥 {d['players']} players</span>
                    </div>
                </div>
                """
                
                # Dedent is crucial here! Streamlit markdown treats 4+ spaces as a code block.
                html_content += textwrap.dedent(html_block)
            
            html_content += '</div>'
            st.markdown(html_content, unsafe_allow_html=True)
