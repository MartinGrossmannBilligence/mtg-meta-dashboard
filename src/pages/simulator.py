import streamlit as st
import pandas as pd
import plotly.express as px
from src.analytics import calculate_expected_winrate
from src.ui import THEME, style_winrate, html_deck_table

def show_simulator(matrix_dict, all_archetypes, records_data):
    st.markdown('<h1 style="font-size: 24px;">Tournament Simulator</h1>', unsafe_allow_html=True)

    st.subheader("1. Field Composition")
    st.caption("Set expected share (%) for each deck. Remaining % auto-assigned to Other Decks. (Defaults pre-filled based on real meta shares)")

    # Get the top decks by total matches, filtering out unknowns, and inject user-requested specific decks
    top_decks = []
    for r in sorted(records_data, key=lambda x: x.get("total_matches", 0), reverse=True):
        arch = r["archetype"]
        if "unknown" not in arch.lower():
            top_decks.append(arch)
        if len(top_decks) >= 8:
            break
            
    for extra in ["Oath Ponza", "Terrageddon", "Stasis"]:
        if extra not in top_decks:
            top_decks.append(extra)

    # Extract real meta shares to use as defaults
    real_meta_shares = matrix_dict.get("meta_shares", {})
    
    meta_shares = {}
    total_assigned = 0

    cols = st.columns(4)
    for i, deck in enumerate(top_decks):
        with cols[i % 4]:
            # Get real share, fallback to 10/5 if missing
            default_share_pct = real_meta_shares.get(deck)
            if default_share_pct is None:
                default_share_pct = real_meta_shares.get(deck.upper())
                
            if default_share_pct is not None:
                default_val = int(round(default_share_pct * 100))
            else:
                default_val = 10 if i < 3 else 5
                
            share = st.slider(f"{deck}", 0, 100, default_val, key=f"sim_sld_{deck}")
            meta_shares[deck] = share / 100
            total_assigned += share

    # Put Other Decks on a dedicated row
    st.markdown('<div style="margin: 20px 0 10px 0; border-top: 1px solid #222222; padding-top: 10px;"></div>', unsafe_allow_html=True)
    remaining = max(0, 100 - total_assigned)
    if total_assigned > 100:
        st.error(f"⚠️ **Other Decks: 0%** — Total exceeds 100% by {total_assigned - 100}%. Results will be normalized automatically.")
    else:
        st.info(f"🔹 **Other Decks:** {remaining}%")

    meta_shares["Other Decks"] = remaining / 100

    col_btn1, col_btn2 = st.columns([0.25, 0.75])
    with col_btn1:
        calc_btn = st.button("Calculate Projected EV", type="primary")
    with col_btn2:
        reset_btn = st.button("Reset to Default Meta")
        
    if reset_btn:
        for j, d in enumerate(top_decks):
            pct = real_meta_shares.get(d) or real_meta_shares.get(d.upper())
            val = int(round(pct * 100)) if pct is not None else (10 if j < 3 else 5)
            st.session_state[f"sim_sld_{d}"] = val
        st.rerun()

    if calc_btn:
        with st.spinner("Simulating..."):
            # matrix_dict is now the full matrix_data object
            matchups_matrix = matrix_dict.get("matrix", matrix_dict)
            evs = calculate_expected_winrate(meta_shares, matchups_matrix, all_archetypes)
            ev_df = pd.DataFrame(list(evs.items()), columns=["Deck", "Projected Win Rate"])
            # Remove "Unknown" deck from the output pool before ranking
            ev_df = ev_df[ev_df["Deck"] != "Unknown"]
            ev_df = ev_df.sort_values("Projected Win Rate", ascending=False).reset_index(drop=True)
            ev_df["#"] = ev_df.index + 1

            st.divider()

            st.markdown("<h3>Best Deck for the Field</h3>", unsafe_allow_html=True)
            d = ev_df[["#", "Deck", "Projected Win Rate"]].head(10).copy()
            d["Projected Win Rate"] = d["Projected Win Rate"].map(lambda x: f"{x:.1%}")
            
            # Show the table full-width, centered
            _, tbl_col, _ = st.columns([0.1, 0.8, 0.1])
            with tbl_col:
                st.markdown(html_deck_table(d, ["#", "Deck", "Projected Win Rate"], wr_col="Projected Win Rate"), unsafe_allow_html=True)


