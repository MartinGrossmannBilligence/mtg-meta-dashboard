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

    try:
        default_idx = all_archetypes.index("Blue/Black Psychatog")
    except ValueError:
        default_idx = 0
    target_deck = st.selectbox("Select Deck", all_archetypes, index=default_idx)

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
                    <div style="font-size:11px; color:#8A8A8A; margin-bottom:2px; text-transform:uppercase; letter-spacing:0.06em;" title="{good_n} favoured (>55%) · {even_n} even (45–55%) · {bad_n} unfavoured (<45%)">Matchup Distribution</div>
                    <div style="font-size: 1.8rem; font-weight: 500;" title="{good_n} good, {even_n} even, {bad_n} bad">{colored_text}</div>
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

    # --- TOP 5 / WORST 5 ---
    col_best, col_worst = st.columns(2)

    def _table(df_slice):
        d = df_slice[["Opponent", "WR", "Games", "Record"]].copy()
        d = d.rename(columns={"WR": "Win Rate"})
        d["Win Rate"] = d["Win Rate"].map(lambda x: f"{x:.1%}")
        return _style_wr_col(d)

    with col_best:
        col_best.markdown("###### Top 5 Best Matchups")
    if not df_prof.empty:
        col_best.dataframe(_table(df_prof.head(5)), use_container_width=True, hide_index=True)

    col_worst.markdown("###### Top 5 Worst Matchups")
    # Zde bylo potřeba sort_values("WR", ascending=True) pro odřazení od nejhoršího
    if not df_prof.empty:
        col_worst.dataframe(_table(df_prof.tail(5).sort_values("WR", ascending=True)), use_container_width=True, hide_index=True)

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

    st.markdown('<div style="margin: 8px 0 12px 0; border-top: 1px solid #222222;"></div>', unsafe_allow_html=True)

    # --- WIN RATE HISTORY ---
    st.subheader("Win Rate Trend")
    st.caption("Overall win rate across time windows — All Time → 2Y → 1Y → 6M.")

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
            height=300,
            paper_bgcolor=THEME["surface"], plot_bgcolor="rgba(0,0,0,0)",
            font_color=THEME["muted"],
            font_family="IBM Plex Mono",
            margin=dict(l=0, r=0, t=30, b=0),
            yaxis=dict(tickformat=".0%", range=[0.3, 0.7], tickfont=dict(size=12)),
            xaxis=dict(tickfont=dict(size=13)),
            xaxis_title="", yaxis_title="",
        )
        st.plotly_chart(fig_hist, use_container_width=True)
