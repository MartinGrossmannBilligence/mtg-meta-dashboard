import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.analytics import load_period_data, wilson_score_interval, calculate_polarity, get_period_comparison
from src.ui import THEME, style_winrate

def _quality_badge(games):
    if games >= 50: return "High"
    if games >= 20: return "Avg"
    return "Low"

def show_analysis(matrix_dict, all_archetypes, records_data, data_dir, timeframes):
    st.markdown("<h1>Deck Analysis</h1>", unsafe_allow_html=True)
    st.markdown('<p style="color:#8A8A8A; font-size:13px; margin-top:-20px; margin-bottom:24px;">Premodern Metagame · Data: Duress Crew · Individual Deck Deep-Dive</p>', unsafe_allow_html=True)

    target_deck = st.selectbox("SELECT DECK", all_archetypes)

    row_data = matrix_dict.get(target_deck, {})
    deck_record = next((r for r in records_data if r["archetype"] == target_deck), {})
    overall_wr = deck_record.get("win_rate", 0)
    total_games = deck_record.get("total_matches", 0)

    # Build matchup rows (with confidence intervals)
    prof_rows = []
    for other in all_archetypes:
        if other == target_deck: continue
        cell = row_data.get(other, {})
        total = cell.get("total_matches", 0)
        if total > 0:
            wins = cell.get("wins", 0)
            wr = cell.get("win_rate", 0.5)
            lo, hi = wilson_score_interval(wins, total)
            prof_rows.append({
                "Opponent": other,
                "Win Rate": wr,
                "95% CI": f"{lo:.1%} – {hi:.1%}",
                "Record": f"{wins}W – {cell.get('losses',0)}L",
                "Games": total,
                "Sample": _quality_badge(total),
            })

    df_prof = pd.DataFrame(prof_rows).sort_values("Win Rate", ascending=False)

    # Polarity + percentile context
    all_polarity = []
    for a in all_archetypes:
        v = calculate_polarity(a, matrix_dict, all_archetypes)
        all_polarity.append(v)
    polarity = calculate_polarity(target_deck, matrix_dict, all_archetypes)
    # percentile rank (0=most stable, 100=most polar)
    pct_rank = int(100 * sum(p <= polarity for p in all_polarity) / max(len(all_polarity), 1))

    # --- KPI ROW (without best/worst) ---
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Overall Win Rate", f"{overall_wr:.1%}")
    kpi2.metric("Total Games", total_games)
    kpi3.metric(
        "Polarity Index",
        f"{polarity*100:.1f}%",
        help=f"Measures how polarizing this deck is (high variance matchups). This deck ranks at the {pct_rank}th percentile — "
             f"{'high polarity, strong matchup spread' if pct_rank > 66 else 'average polarity' if pct_rank > 33 else 'stable, consistent matchup profile'}. "
             f"0% = perfectly even matchups, 100% = extreme rock-paper-scissors."
    )

    st.divider()

    # --- DISTRIBUTION CHART (full width between KPIs and top5) ---
    if not df_prof.empty:
        df_prof["Bracket"] = pd.cut(
            df_prof["Win Rate"],
            bins=[0, 0.45, 0.55, 1.0],
            labels=["Unfavoured (<45%)", "Even (45–55%)", "Favoured (>55%)"]
        )
        dist = (
            df_prof["Bracket"]
            .value_counts()
            .reindex(["Unfavoured (<45%)", "Even (45–55%)", "Favoured (>55%)"])
            .reset_index()
        )
        dist.columns = ["Category", "Count"]
        fig_dist = px.bar(
            dist, x="Category", y="Count",
            color="Category",
            color_discrete_map={
                "Unfavoured (<45%)": THEME["danger"],
                "Even (45–55%)": THEME["warning"],
                "Favoured (>55%)": THEME["success"],
            },
            template="plotly_dark",
        )
        fig_dist.update_layout(
            showlegend=False, height=220,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis_title="", yaxis_title="COUNT",
        )
        st.plotly_chart(fig_dist, use_container_width=True)

    st.divider()

    # --- TOP 5 / WORST 5 ---
    col_best, col_worst = st.columns(2)
    with col_best:
        st.subheader("Top 5 Best Matchups")
        if not df_prof.empty:
            d = df_prof.head(5)[["Opponent", "Win Rate", "Games", "Record"]].copy()
            d["Win Rate"] = d["Win Rate"].map(lambda x: f"{x:.1%}")
            st.dataframe(d.style.applymap(style_winrate, subset=["Win Rate"]), use_container_width=True, hide_index=True)

    with col_worst:
        st.subheader("Top 5 Worst Matchups")
        if not df_prof.empty:
            d = df_prof.tail(5)[["Opponent", "Win Rate", "Games", "Record"]].copy()
            d["Win Rate"] = d["Win Rate"].map(lambda x: f"{x:.1%}")
            st.dataframe(d.style.applymap(style_winrate, subset=["Win Rate"]), use_container_width=True, hide_index=True)

    st.divider()

    # --- FULL MATCHUP TABLE with CI and quality badge ---
    st.subheader("All Matchups")
    if not df_prof.empty:
        df_display = df_prof[["Opponent", "Win Rate", "95% CI", "Record", "Games", "Sample"]].copy()
        df_display["Win Rate"] = df_display["Win Rate"].map(lambda x: f"{x:.1%}")
        st.dataframe(
            df_display.style.applymap(style_winrate, subset=["Win Rate"]),
            use_container_width=True, hide_index=True
        )

    st.divider()

    # --- WIN RATE HISTORY across periods ---
    st.subheader("Win Rate History")
    st.caption("How this deck's overall win rate evolved across different time windows.")

    ordered_periods = list(timeframes.keys())  # All Time, 2Y, 1Y, 6M
    history_rows = []
    for period_label, period_key in timeframes.items():
        try:
            mdata, rdata = load_period_data(data_dir, period_key)
            rec = next((r for r in rdata if r["archetype"] == target_deck), None)
            if rec:
                history_rows.append({
                    "Period": period_label,
                    "Win Rate": rec["win_rate"],
                    "Games": rec["total_matches"],
                })
        except Exception:
            pass

    if history_rows:
        df_hist = pd.DataFrame(history_rows)
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Scatter(
            x=df_hist["Period"], y=df_hist["Win Rate"],
            mode="lines+markers+text",
            text=[f"{v:.1%}" for v in df_hist["Win Rate"]],
            textposition="top center",
            line=dict(color=THEME["text"], width=2),
            marker=dict(size=8, color=THEME["text"]),
        ))
        fig_hist.add_hline(y=0.5, line_dash="dash", line_color=THEME["faint"])
        fig_hist.update_layout(
            height=280,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color=THEME["text"],
            margin=dict(l=0, r=0, t=20, b=0),
            yaxis=dict(tickformat=".0%", range=[0.3, 0.7]),
            xaxis_title="", yaxis_title="Win Rate",
        )
        st.plotly_chart(fig_hist, use_container_width=True)

        df_hist_display = df_hist.copy()
        df_hist_display["Win Rate"] = df_hist_display["Win Rate"].map(lambda x: f"{x:.1%}")
        st.dataframe(df_hist_display.style.applymap(style_winrate, subset=["Win Rate"]), use_container_width=True, hide_index=True)
