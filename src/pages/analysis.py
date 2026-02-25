import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.analytics import load_period_data, wilson_score_interval, calculate_polarity
from src.ui import THEME, style_winrate
import os
import json
import base64

_icon_cache = {}
def _get_icon_b64(deck_name, data_dir="data"):
    """Return base64-encoded JPEG art_crop for a deck (cached)."""
    if deck_name in _icon_cache:
        return _icon_cache[deck_name]
    slug = deck_name.lower().replace(" ", "_").replace("/", "_").replace("'", "")
    path = os.path.join(data_dir, "..", "assets", "deck_icons", f"{slug}.jpg")
    if os.path.exists(path):
        with open(path, "rb") as f:
            _icon_cache[deck_name] = base64.b64encode(f.read()).decode()
    else:
        _icon_cache[deck_name] = None
    return _icon_cache[deck_name]

def _wr_color_str(wr_str):
    """Return CSS color for a formatted win rate string like '55.0%'."""
    try:
        v = float(wr_str.strip('%')) / 100
    except:
        return THEME['text']
    if v > 0.55: return THEME['success']
    if v < 0.45: return THEME['danger']
    if v < 0.50: return THEME['warning']
    return THEME['text']

def _html_matchup_table(df, columns, data_dir="data"):
    """Render a matchup dataframe as an HTML table with deck icons."""
    header = ''.join(f'<th style="padding:6px 8px; text-align:left; border-bottom:1px solid #333; color:#8A8A8A; font-size:13px;">{c}</th>' for c in columns)
    rows_html = ''
    for _, row in df.iterrows():
        cells = ''
        for c in columns:
            val = str(row.get(c, ''))
            if c == 'Opponent':
                b64 = _get_icon_b64(val, data_dir)
                img = f'<img src="data:image/jpeg;base64,{b64}" style="width:28px;height:20px;object-fit:cover;border-radius:3px;margin-right:6px;vertical-align:middle;border:1px solid #333;">' if b64 else ''
                cells += f'<td style="padding:5px 8px; font-size:14px;">{img}{val}</td>'
            elif c == 'Win Rate':
                color = _wr_color_str(val)
                cells += f'<td style="padding:5px 8px; font-size:14px; color:{color}; font-weight:600;">{val}</td>'
            else:
                cells += f'<td style="padding:5px 8px; font-size:14px; color:#AAA;">{val}</td>'
        rows_html += f'<tr style="border-bottom:1px solid #222;">{cells}</tr>'
    return f'<table style="width:100%; border-collapse:collapse; background:#1A1A1A; border-radius:8px; overflow:hidden;"><thead><tr>{header}</tr></thead><tbody>{rows_html}</tbody></table>'

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
    st.markdown('<h1 style="font-size: 24px;">Deck Analysis</h1>', unsafe_allow_html=True)

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

    # Icon + selectbox side by side
    col_icon, col_select = st.columns([0.08, 0.92])
    with col_select:
        target_deck = st.selectbox(
            "Select Deck", 
            all_archetypes, 
            index=current_idx
        )
    st.session_state["analysis_saved_deck"] = target_deck

    with col_icon:
        b64 = _get_icon_b64(target_deck, data_dir)
        if b64:
            st.markdown(
                f'<div style="margin-top:24px;">'
                f'<img src="data:image/jpeg;base64,{b64}" style="width:56px; height:42px; object-fit:cover; border-radius:6px; border:1px solid #333;">'
                f'</div>',
                unsafe_allow_html=True,
            )

    # matrix_dict is now the full matrix_data object
    matchups_matrix = matrix_dict.get("matrix", matrix_dict) # fallback for old Duress files that are flat
    row_data        = matchups_matrix.get(target_deck, {})
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
    if not df_prof.empty:
        df_prof = df_prof[df_prof["Opponent"] != "Unknown"]

    # Polarity percentile — must use inner matchups_matrix, not the full matrix_dict
    matchups_matrix_for_polarity = matrix_dict.get("matrix", matrix_dict)
    all_polarities = [calculate_polarity(a, matchups_matrix_for_polarity, all_archetypes) for a in all_archetypes]
    polarity       = calculate_polarity(target_deck, matchups_matrix_for_polarity, all_archetypes)
    pct_rank       = int(100 * sum(p <= polarity for p in all_polarities) / max(len(all_polarities), 1))
    pct_label      = (
        "high polarity — strong matchup spread (rock-paper-scissors)" if pct_rank > 66
        else "average polarity" if pct_rank > 33
        else "stable — consistent matchup profile across the field"
    )

    tab_stats, tab_decks = st.tabs(["Statistics", "Top Decklists"])

    with tab_stats:
        # matrix_dict is now the full matrix_data object
        matchups_matrix = matrix_dict.get("matrix", matrix_dict)
        meta_shares     = matrix_dict.get("meta_shares", {})
        share = meta_shares.get(target_deck)
        if share is None: share = meta_shares.get(target_deck.upper())
        share_display = f"{share:.1%}" if share is not None else "N/A"

        # --- KPI ROW (5 columns) ---
        c1, c2, c3, c4, c5 = st.columns(5)
        
        with c1:
            st.metric("Overall Win Rate", f"{overall_wr:.1%}")
        with c2:
            st.metric("Total Games", f"{total_games:,}")
        with c3:
            st.metric("Meta Share", share_display)
        with c4:
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

                st.metric(
                    "Matchup Distribution",
                    f"{good_n}↑  {even_n}~  {bad_n}↓",
                    help=f"{good_n} favoured (>55%) · {even_n} even (45–55%) · {bad_n} unfavoured (<45%)"
                )
        with c5:
            st.metric(
                "Polarity Index",
                f"{polarity * 100:.1f}%",
                help=f"Spread of matchup win rates. {pct_rank}th percentile — {pct_label}.",
            )

        st.markdown('<div style="margin: 8px 0 12px 0; border-top: 1px solid #222222;"></div>', unsafe_allow_html=True)

        st.markdown(
            "<h3>Win Rate &amp; Meta Share Trend "
            "<span title='Each point shows the overall win rate and metagame share across all recorded matches in that time window.' "
            "style='cursor:help; font-size:16px; color:#8A8A8A; opacity:0.8;'>&#9432;</span></h3>",
            unsafe_allow_html=True,
        )
    


        history_rows = []
        for period_label, period_key in timeframes.items():
            try:
                mdata, rdata = load_period_data(data_dir, period_key)
                rec = next((r for r in rdata if r["archetype"] == target_deck), None)
                if rec:
                    ms = mdata.get("meta_shares", {})
                    share = ms.get(target_deck)
                    if share is None: share = ms.get(target_deck.upper())
                    history_rows.append({
                        "Period":      period_label,
                        "Win Rate":    rec["win_rate"],
                        "Meta Share":  share,
                        "Games":       rec["total_matches"],
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

            # ── Combined chart: Win Rate + Meta Share, shared left y-axis ──────
            ms_vals = df_hist["Meta Share"].tolist()
            has_meta = any(v is not None for v in ms_vals)

            fig_hist = go.Figure()
            fig_hist.add_trace(go.Scatter(
                x=df_hist["Period"], y=df_hist["Win Rate"],
                name="Win Rate",
                mode="lines+markers+text",
                text=[f"{v:.1%}" for v in df_hist["Win Rate"]],
                textposition="top center",
                textfont=dict(size=13, color=[_wr_color(v) for v in df_hist["Win Rate"]]),
                line=dict(color="#E8E8E8", width=3, dash="dot"),
                marker=dict(size=9, color=[_wr_color(v) for v in df_hist["Win Rate"]], line=dict(width=0)),
            ))

            if has_meta:
                ms_display = [v if v is not None else None for v in ms_vals]
                fig_hist.add_trace(go.Scatter(
                    x=df_hist["Period"], y=ms_display,
                    name="Meta Share",
                    mode="lines+markers+text",
                    text=[f"{v:.1%}" if v is not None else "" for v in ms_display],
                    textposition="top center",
                    textfont=dict(size=13, color="rgba(190, 220, 240, 0.85)"),
                    line=dict(color="rgba(190, 220, 240, 0.95)", width=3, dash="dot"),
                    marker=dict(size=8, color="rgba(190, 220, 240, 0.95)"),
                    connectgaps=False,
                ))


            # Add inline label at the last point of each line
            last_period = df_hist["Period"].iloc[-1]
            last_wr     = df_hist["Win Rate"].iloc[-1]
            fig_hist.add_annotation(
                x=last_period, y=last_wr,
                text="Win Rate", showarrow=False,
                xanchor="left", yanchor="middle", xshift=10,
                font=dict(size=13, color=THEME["muted"]),
            )
            if has_meta:
                last_ms = next((v for v in reversed(ms_display) if v is not None), None)
                last_ms_period = df_hist["Period"].iloc[
                    max(i for i, v in enumerate(ms_display) if v is not None)
                ]
                if last_ms is not None:
                    fig_hist.add_annotation(
                        x=last_ms_period, y=last_ms,
                        text="Meta Share", showarrow=False,
                        xanchor="left", yanchor="middle", xshift=10,
                        font=dict(size=13, color="rgba(190, 220, 240, 0.85)"),
                    )

            fig_hist.update_layout(
                height=210,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color=THEME["muted"], font_family="IBM Plex Mono",
                margin=dict(l=35, r=90, t=28, b=0),
                yaxis=dict(
                    tickformat=".0%", range=[0, 0.7], tickfont=dict(size=11), 
                    showgrid=True, dtick=0.2, gridcolor="rgba(255, 255, 255, 0.1)"
                ),
                xaxis=dict(tickfont=dict(size=12)),
                xaxis_title="",
                showlegend=False,
                hovermode=False,
            )
            st.plotly_chart(fig_hist, use_container_width=True, key="deck_trend_combined")

        st.markdown('<div style="margin: 8px 0 12px 0; border-top: 1px solid #222222;"></div>', unsafe_allow_html=True)

        # --- TOP 5 / WORST 5 ---
        col_best, col_worst = st.columns(2)

        def _prep(df_slice):
            d = df_slice[["Opponent", "WR", "Games", "Record"]].copy()
            d = d.rename(columns={"WR": "Win Rate"})
            d["Win Rate"] = d["Win Rate"].map(lambda x: f"{x:.1%}")
            return d

        with col_best:
            col_best.markdown("<h3>Best Matchups <span title='Matchups with fewer than 20 games are deprioritized to ensure statistical reliability.' style='cursor:help; font-size:14px; color:#8A8A8A; opacity:0.8;'>&#9432;</span></h3>", unsafe_allow_html=True)
        
        # Split into reliable (>= 20 games) and unreliable (< 20 games)
        if not df_prof.empty:
            df_reliable = df_prof[df_prof["Games"] >= 20].sort_values("WR", ascending=False)
            df_unreliable = df_prof[df_prof["Games"] < 20].sort_values("WR", ascending=False)
            
            best_matchups = df_reliable.head(5)
            if len(best_matchups) < 5:
                needed = 5 - len(best_matchups)
                best_matchups = pd.concat([best_matchups, df_unreliable.head(needed)])
                
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
            col_best.markdown(_html_matchup_table(_prep(best_matchups), ["Opponent", "Win Rate", "Games", "Record"], data_dir), unsafe_allow_html=True)

        col_worst.markdown("<h3>Worst Matchups <span title='Matchups with fewer than 20 games are deprioritized to ensure statistical reliability.' style='cursor:help; font-size:14px; color:#8A8A8A; opacity:0.8;'>&#9432;</span></h3>", unsafe_allow_html=True)
        if not worst_matchups.empty:
            col_worst.markdown(_html_matchup_table(_prep(worst_matchups), ["Opponent", "Win Rate", "Games", "Record"], data_dir), unsafe_allow_html=True)

        st.markdown('<div style="margin: 8px 0 12px 0; border-top: 1px solid #222222;"></div>', unsafe_allow_html=True)

        # --- FULL MATCHUP TABLE ---
        st.subheader("All Matchups")
        if not df_prof.empty:
            df_display = df_prof[["Opponent", "WR", "95% CI", "Record", "Games", "Sample"]].copy()
            df_display = df_display.rename(columns={"WR": "Win Rate", "95% CI": "Confidence Interval", "Sample": "Sample Size"})
            df_display["Win Rate"] = df_display["Win Rate"].map(lambda x: f"{x:.1%}")
            st.markdown(
                _html_matchup_table(df_display, ["Opponent", "Win Rate", "Confidence Interval", "Record", "Games", "Sample Size"], data_dir),
                unsafe_allow_html=True,
            )



    with tab_decks:

        decklists_file = os.path.join(data_dir, "decklists.json")
        decks = []
        if os.path.exists(decklists_file):
            with open(decklists_file, 'r', encoding='utf-8') as f:
                try:
                    all_decklists = json.load(f)
                    decks = all_decklists.get(target_deck, [])
                except Exception as e:
                    pass
                    
        if not decks:
            st.info("No recent decklists found matching the criteria (>=50 players, Top 8).")
        else:
            st.markdown("<br>", unsafe_allow_html=True)
            info_text = "Offline snapshots from MTGDecks.net. Prioritizes Top 8 finishes in events with 50+ players. Searches up to 10 pages deep per archetype. Max 10 decks."
            st.markdown(f"<h3>Recent Top Decklists <span title='{info_text}' style='cursor:help; font-size:16px; color:#8A8A8A; opacity:0.8;'>&#9432;</span></h3>", unsafe_allow_html=True)
            
            # Load Official MTG Mana Symbols from local assets
            def _get_mana_b64(color_code):
                mapping = {'W': 'W', 'U': 'U', 'B': 'B', 'R': 'R', 'G': 'G'}
                code = mapping.get(color_code)
                if not code: return None, "No Code"
                fname = f"mana_{code}_128.webp"
                # Use same logic as deck icons
                path = os.path.join(data_dir, "..", "assets", "mana_symbols", fname)
                
                if not os.path.exists(path):
                    # Fallback to absolute check as secondary
                    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    path = os.path.join(base_dir, "assets", "mana_symbols", fname)
                
                if not os.path.exists(path):
                    return None, path
                    
                with open(path, "rb") as f:
                    return base64.b64encode(f.read()).decode(), path

            MANA_ICONS = {c: _get_mana_b64(c)[0] for c in ['W', 'U', 'B', 'R', 'G']}
            # Add a generic colorless diamond
            MANA_ICONS['C'] = 'PHN2ZyB2aWV3Qm94PSIwIDAgMzIgMzIiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGNpcmNsZSBjeD0iMTYiIGN5PSIxNiIgcj0iMTUiIGZpbGw9IiNBM0EzQTMiIC8+PHBhdGggZD0iTTE2IDhsNiA4bC02IDhsLTYtOHoiIGZpbGw9IiMwMDAiIC8+PC9zdmc+'
            
            import textwrap
            
            # Wrap in a styled container
            html_content = '<div style="background-color: #1A1A1A; border: 1px solid #2A2A2A; border-radius: 8px; padding: 16px;">'
            
            for i, d in enumerate(decks):
                # Replace title hover with actual clickable details disclosure
                cards = d.get('cards', [])
                if cards:
                    lines = []
                    for c in cards:
                        lines.append(f"{c['qty']}x {c['name']}")
                    decklist_html = "<br>".join(lines)
                    decklist_preview = f'<details style="margin-top:8px;"><summary style="cursor:pointer; color:#8A8A8A; font-size:13px; user-select:none;">&#128065; View Decklist</summary><div style="margin-top:8px; padding:10px; background:rgba(0,0,0,0.3); border-radius:6px; font-size:12px; color:#D0D0D0; display:grid; grid-template-columns:repeat(auto-fill, minmax(180px, 1fr)); gap:4px;">{decklist_html}</div></details>'
                else:
                    decklist_preview = ""
                
                # Render colors as mana symbols
                color_dots = ""
                for c in d.get("colors", []):
                    b64 = MANA_ICONS.get(c)
                    if b64:
                        mime = "image/svg+xml" if c == 'C' else "image/webp"
                        color_dots += f'<img src="data:{mime};base64,{b64}" style="width:16px; height:16px; margin-right:4px; vertical-align:middle;" title="Mana {c}" alt="[{c}]">'
                
                # Render spiciness badge if > 0
                spice = d.get('spice', 0)
                spice_badge = ""
                if spice > 0:
                    spice_color = "#E49977" if spice > 50 else "#F59F00" if spice > 20 else "#8A8A8A"
                    spice_badge = f'<span style="margin-left:8px; font-size:10px; color:{spice_color}; border:1px solid {spice_color}40; padding:1px 6px; border-radius:10px; background:rgba(0,0,0,0.2);">🌶️ Spice: {spice}%</span>'
                
                border_bottom = 'border-bottom: 1px solid #2A2A2A;' if i < len(decks) - 1 else ''
                margin_bottom = 'margin-bottom: 12px; padding-bottom: 12px;' if i < len(decks) - 1 else ''
                
                html_block = (
                    f'<div style="{margin_bottom} {border_bottom}">'
                    f'<div style="display:flex; align-items:center; margin-bottom: 2px;">'
                    f'<a href="{d["url"]}" target="_blank" style="text-decoration:none; color:inherit; margin-right:12px; font-size:14px;">'
                    f'<span style="color:#E0E0E0;"><strong style="color:#FFF;">{d["rank"]}</strong> from <strong style="color:#FFF;">{d.get("players", "??")}</strong> Players</span>'
                    f'</a>'
                    f'<a href="{d["url"]}" target="_blank" style="color:#6BC78E; text-decoration:none; margin-right:10px; font-size:15px; font-weight:600;">{d["player"]}</a>'
                    f'{color_dots}'
                    f'{spice_badge}'
                    f'</div>'
                    f'<div style="font-size:12px; color:#8A8A8A; display:flex; gap:12px; margin-top:4px;">'
                    f'<span>🗓️ {d["date"]}</span>'
                    f'<span>🏆 {d["event"]}</span>'
                    f'<span>👥 {d["players"]} players</span>'
                    f'</div>'
                    f'{decklist_preview}'
                    f'</div>'
                )
                
                html_content += html_block
            
            html_content += '</div>'
            st.markdown(html_content, unsafe_allow_html=True)
