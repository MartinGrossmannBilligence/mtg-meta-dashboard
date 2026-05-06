import streamlit as st
import re
import math
import time
import urllib.request
import urllib.parse
import json
import base64
import os
from src.ui import THEME, html_kpi_card

COLORS = ["W", "U", "B", "R", "G"]
COLOR_NAMES = {"W": "White", "U": "Blue", "B": "Black", "R": "Red", "G": "Green"}

# ── Mana symbol images (base64) ───────────────────────────────────────────────
_ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "mana_symbols")

def _load_symbol_b64(color: str) -> str:
    for ext in ("webp", "png"):
        path = os.path.join(_ASSETS, f"mana_{color}_128.{ext}")
        if os.path.exists(path):
            with open(path, "rb") as f:
                return f"data:image/{ext};base64,{base64.b64encode(f.read()).decode()}"
    return ""

_MANA_B64: dict[str, str] = {c: _load_symbol_b64(c) for c in COLORS}

def mana_img(color: str, size: int = 18) -> str:
    """Return an inline <img> tag for a mana pip symbol."""
    src = _MANA_B64.get(color, "")
    if not src:
        return f"<span style='font-size:{size}px;'>{color}</span>"
    return (
        f"<img src='{src}' width='{size}' height='{size}' "
        f"style='vertical-align:middle;margin:0 1px;' alt='{color}'/>"
    )

def mana_cost_html(pips: dict, size: int = 16) -> str:
    """'{W':1, 'U':1} → two inline pip images."""
    parts = []
    for c in COLORS:
        count = int(math.ceil(pips.get(c, 0)))
        parts.extend([mana_img(c, size)] * count)
    return "".join(parts) or "—"

# Frank Karsten: cheap cantrips allow playing fewer lands (~0.28 each)
CANTRIP_SAVINGS = {
    "brainstorm": 0.28,
    "portent": 0.28,
    "opt": 0.28,
    "sleight of hand": 0.28,
    "impulse": 0.28,
    "serum visions": 0.28,
    "ponder": 0.28,
    "preordain": 0.28,
    "careful study": 0.14,
    "accumulated knowledge": 0.14,
    "telling time": 0.14,
    "scroll rack": 0.14,
    "lat-nam's legacy": 0.14,
}

# Hardcoded produced_mana for all common Premodern lands.
# Keys are lowercase card names. Value: list of color symbols produced.
# This avoids Scryfall API calls for lands (which are finite and well-known).
_LT = "Land"
_BL = "Basic Land"
PREMODERN_LAND_DATA: dict[str, tuple[list[str], str]] = {
    # ── Basics ────────────────────────────────────────────────────────────────
    "plains":                    (["W"], f"{_BL} — Plains"),
    "island":                    (["U"], f"{_BL} — Island"),
    "swamp":                     (["B"], f"{_BL} — Swamp"),
    "mountain":                  (["R"], f"{_BL} — Mountain"),
    "forest":                    (["G"], f"{_BL} — Forest"),
    "snow-covered plains":       (["W"], f"{_BL} — Plains"),
    "snow-covered island":       (["U"], f"{_BL} — Island"),
    "snow-covered swamp":        (["B"], f"{_BL} — Swamp"),
    "snow-covered mountain":     (["R"], f"{_BL} — Mountain"),
    "snow-covered forest":       (["G"], f"{_BL} — Forest"),
    # ── Original Duals ────────────────────────────────────────────────────────
    "tundra":                    (["W", "U"], _LT),
    "underground sea":           (["U", "B"], _LT),
    "badlands":                  (["B", "R"], _LT),
    "taiga":                     (["R", "G"], _LT),
    "savannah":                  (["G", "W"], _LT),
    "scrubland":                 (["W", "B"], _LT),
    "volcanic island":           (["U", "R"], _LT),
    "bayou":                     (["B", "G"], _LT),
    "plateau":                   (["R", "W"], _LT),
    "tropical island":           (["G", "U"], _LT),
    # ── Onslaught Fetch Lands ─────────────────────────────────────────────────
    "flooded strand":            (["W", "U"], _LT),
    "polluted delta":            (["U", "B"], _LT),
    "bloodstained mire":         (["B", "R"], _LT),
    "wooded foothills":          (["R", "G"], _LT),
    "windswept heath":           (["G", "W"], _LT),
    # ── Mirage Fetch Lands ────────────────────────────────────────────────────
    "flood plain":               (["W", "U"], _LT),
    "bad river":                 (["U", "B"], _LT),
    "rocky tar pit":             (["B", "R"], _LT),
    "mountain valley":           (["R", "G"], _LT),
    "grasslands":                (["G", "W"], _LT),
    # ── Pain Lands ────────────────────────────────────────────────────────────
    "adarkar wastes":            (["W", "U"], _LT),
    "underground river":         (["U", "B"], _LT),
    "sulfurous springs":         (["B", "R"], _LT),
    "karplusan forest":          (["R", "G"], _LT),
    "brushland":                 (["G", "W"], _LT),
    "caves of koilos":           (["W", "B"], _LT),
    "shivan reef":               (["U", "R"], _LT),
    "llanowar wastes":           (["B", "G"], _LT),
    "battlefield forge":         (["R", "W"], _LT),
    "yavimaya coast":            (["G", "U"], _LT),
    # ── Invasion Lair Lands (tap for one of three colors) ─────────────────────
    "dromar's cavern":           (["W", "U", "B"], _LT),
    "treva's ruins":             (["G", "W", "U"], _LT),
    "darigaaz's caldera":        (["B", "R", "G"], _LT),
    "crosis's catacombs":        (["U", "B", "R"], _LT),
    "rith's grove":              (["R", "G", "W"], _LT),
    # ── Filter Lands ─────────────────────────────────────────────────────────
    "adarkar wastes":            (["W", "U"], _LT),   # duplicate key safe, last wins
    # ── 5-color / Any-color Lands ─────────────────────────────────────────────
    "city of brass":             (["W", "U", "B", "R", "G"], _LT),
    "undiscovered paradise":     (["W", "U", "B", "R", "G"], _LT),
    "gemstone mine":             (["W", "U", "B", "R", "G"], _LT),
    "reflecting pool":           (["W", "U", "B", "R", "G"], _LT),
    "grand coliseum":            (["W", "U", "B", "R", "G"], _LT),
    "forbidden orchard":         (["W", "U", "B", "R", "G"], _LT),
    "mana confluence":           (["W", "U", "B", "R", "G"], _LT),
    "chromatic lantern":         (["W", "U", "B", "R", "G"], _LT),  # not a land but harmless
    # ── Mono-color Special Lands ─────────────────────────────────────────────
    "tolarian academy":          (["U"], _LT),
    "gaea's cradle":             (["G"], _LT),
    "serra's sanctum":           (["W"], _LT),
    "phyrexian tower":           (["B"], _LT),
    "shivan gorge":              (["R"], _LT),
    "library of alexandria":     (["U"], _LT),
    "high market":               (["W"], _LT),
    "hall of the bandit lord":   (["R"], _LT),
    "den of the bugbear":        (["R"], _LT),
    "cave of koilos":            (["W", "B"], _LT),
    # ── Colorless / Utility Lands (no colored mana production) ───────────────
    "wasteland":                 ([], _LT),
    "strip mine":                ([], _LT),
    "ancient tomb":              ([], _LT),
    "city of traitors":          ([], _LT),
    "rishadan port":             ([], _LT),
    "mishra's factory":          ([], _LT),
    "urza's mine":               ([], _LT),
    "urza's tower":              ([], _LT),
    "urza's power plant":        ([], _LT),
    "maze of ith":               ([], _LT),
    "the tabernacle at pendrell vale": ([], _LT),
    "bazaar of baghdad":         ([], _LT),
    "karakas":                   (["W"], _LT),
    "kjeldoran outpost":         (["W"], _LT),
    "soldevi excavations":       (["U"], _LT),
    "kjeldoran dead":            ([], _LT),  # not a land
    "petrified field":           ([], _LT),
    "dust bowl":                 ([], _LT),
    "ghost quarter":             ([], _LT),
    "horizon canopy":            (["G", "W"], _LT),
    "murmuring bosk":            (["G", "W"], _LT),
    "sea of clouds":             (["W", "U"], _LT),
    "morphic pool":              (["U", "B"], _LT),
    "luxury suite":              (["B", "R"], _LT),
    "spire garden":              (["R", "G"], _LT),
    "bountiful promenade":       (["G", "W"], _LT),
    "tsabo's web":               ([], _LT),   # not a land
    # ── Taplands (Invasion, Apocalypse, etc.) ────────────────────────────────
    "coastal tower":             (["W", "U"], _LT),
    "urborg volcano":            (["U", "B"], _LT),
    "tainted isle":              (["U", "B"], _LT),
    "tainted field":             (["W", "B"], _LT),
    "tainted wood":              (["B", "G"], _LT),
    "tainted peak":              (["B", "R"], _LT),
    "salt marsh":                (["U", "B"], _LT),
    "elfhame palace":            (["G", "W"], _LT),
    "shivan oasis":              (["R", "G"], _LT),
    "irrigation ditch":          (["W", "U"], _LT),
    "geothermal crevice":        (["B", "R"], _LT),
    "peat bog":                  (["B"], _LT),
    "river delta":               (["U", "B"], _LT),
    "tinder farm":               (["R", "G"], _LT),
    "rushwood grove":            (["G", "W"], _LT),
    "sulfur vent":               (["B", "R"], _LT),
    "mountain stronghold":       (["R"], _LT),
    "skyshroud forest":          (["G", "U"], _LT),
}

# Karsten 90%-consistency source minimums: (pip_count, target_turn) → sources needed
# Based on 60-card deck, on the play
KARSTEN_SOURCES = {
    (1, 1): 14, (1, 2): 13, (1, 3): 12, (1, 4): 11,
    (2, 2): 21, (2, 3): 18, (2, 4): 16,
    (3, 3): 23, (3, 4): 20,
}


@st.cache_data(ttl=604800, show_spinner=False)  # 7-day cache, shared across sessions on Cloud
def _scryfall_fetch(card_name: str) -> dict | None:
    """Fetch card data from Scryfall. Retries once on 429 rate-limit."""
    # Check hardcoded land data first — never hits the API for known lands
    key = card_name.lower().strip()
    if key in PREMODERN_LAND_DATA:
        produced, type_line = PREMODERN_LAND_DATA[key]
        return {"object": "card", "name": card_name, "type_line": type_line,
                "mana_cost": "", "produced_mana": produced}

    url = f"https://api.scryfall.com/cards/named?fuzzy={urllib.parse.quote(card_name)}"
    headers = {"User-Agent": "PremodernLab/1.0", "Accept": "application/json"}

    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt == 0:
                time.sleep(2.0)  # back off and retry once
                continue
            return None  # 404 not found or other error
        except Exception:
            return None
    return None


def _parse_decklist(text: str) -> list[tuple[int, str]]:
    cards = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("//") or line.startswith("#"):
            continue
        if re.match(r'^SB:', line, re.IGNORECASE):
            continue
        m = re.match(r'^(\d+)x?\s+(.+)$', line)
        if m:
            cards.append((int(m.group(1)), m.group(2).strip()))
    return cards


def _parse_mana_cost(mc: str) -> dict:
    """'{2}{W}{U}' → {'cmc': 4, 'pips': {'W':1,'U':1,...}}"""
    pips = {c: 0 for c in COLORS}
    cmc = 0
    for token in re.findall(r'\{([^}]+)\}', mc.upper()):
        if token.isdigit():
            cmc += int(token)
        elif token in COLORS:
            pips[token] += 1
            cmc += 1
        elif "/" in token:
            # Hybrid mana e.g. {W/U} — counts as 1 CMC, adds 0.5 to each color
            parts = [p for p in token.split("/") if p in COLORS]
            for p in parts:
                pips[p] += 0.5
            cmc += 1
        elif token == "X":
            pass  # X spells: ignore for CMC
        elif token not in ("S", "C", "T"):
            try:
                cmc += int(token)
            except ValueError:
                pass
    return {"cmc": cmc, "pips": pips}


def _hypergeom_at_least(N: int, K: int, n: int, k: int) -> float:
    """P(X >= k) for X ~ Hypergeometric(N, K, n). Draws without replacement."""
    if k <= 0:
        return 1.0
    if K < k:
        return 0.0
    n = min(n, N)
    total = math.comb(N, n)
    if total == 0:
        return 0.0
    prob = sum(
        math.comb(K, i) * math.comb(max(0, N - K), max(0, n - i))
        for i in range(k, min(K, n) + 1)
    ) / total
    return min(1.0, max(0.0, prob))


def show_mana_check():
    st.markdown('<h1 class="page-title">Mana Check</h1>', unsafe_allow_html=True)
    st.caption(
        "Paste your decklist to get recommended land count, color source checks, "
        "and per-spell casting probability on curve."
    )

    col_input, col_settings = st.columns([0.62, 0.38])

    with col_settings:
        st.subheader("Settings")
        on_draw = st.toggle(
            "On the draw",
            value=False,
            help="On the draw you see 1 extra card — slightly improves consistency.",
        )
        target_pct = st.slider("Target consistency", 50, 99, 90, format="%d%%")
        deck_size = st.number_input("Deck size", min_value=40, max_value=100, value=60, step=1)
        manual_cantrips = st.toggle(
            "Set cantrip count manually",
            value=False,
            help=(
                "By default, cantrips (Brainstorm, Portent, Opt, Sleight of Hand, Impulse…) "
                "are auto-detected from your decklist. Toggle this on to enter the count yourself."
            ),
        )
        cantrip_manual_value = 0
        if manual_cantrips:
            cantrip_manual_value = st.number_input(
                "Cantrip count",
                min_value=0, max_value=40, value=0, step=1,
                help="Total copies of cheap draw/filter spells that reduce your land requirement by ~0.28 each.",
            )

    with col_input:
        st.subheader("Decklist")
        st.caption("One card per line: `4 Dark Ritual`  ·  SB: lines are ignored.")
        decklist_text = st.text_area(
            "Decklist",
            height=340,
            placeholder=(
                "4 Dark Ritual\n"
                "4 Hypnotic Specter\n"
                "4 Nevinyrral's Disk\n"
                "4 Brainstorm\n"
                "...\n"
                "20 Swamp"
            ),
            label_visibility="collapsed",
        )
        analyze_btn = st.button("Analyze Mana", type="primary")

    if not analyze_btn or not decklist_text.strip():
        _how_it_works()
        return

    # ── Parse ─────────────────────────────────────────────────────────────────
    raw_cards = _parse_decklist(decklist_text)
    if not raw_cards:
        st.error("Could not parse decklist. Each line must start with a number: `4 Card Name`.")
        return

    # ── Scryfall lookups ──────────────────────────────────────────────────────
    unique_names = list({name for _, name in raw_cards})
    card_data: dict[str, dict] = {}
    not_found: list[str] = []

    prog = st.progress(0, text="Looking up cards on Scryfall…")
    for idx, name in enumerate(unique_names):
        data = _scryfall_fetch(name)
        if data and data.get("object") == "card":
            card_data[name] = data
        else:
            not_found.append(name)
        time.sleep(0.1)  # 100ms between requests — Scryfall recommends ≥50ms
        prog.progress((idx + 1) / len(unique_names), text=f"Scryfall: {name}")
    prog.empty()

    if not_found:
        st.warning(f"Not found on Scryfall (check spelling): {', '.join(not_found)}")

    # ── Classify cards ────────────────────────────────────────────────────────
    lands: list[tuple[int, str, list[str]]] = []       # (qty, name, produced_colors)
    spells: list[tuple[int, str, float, dict]] = []     # (qty, name, cmc, pips)
    mana_perms: list[tuple[int, str, list[str]]] = []   # non-land mana permanents (Mox, dorks…)
    auto_cantrip_adj = 0.0

    for qty, name in raw_cards:
        d = card_data.get(name)
        if d is None:
            continue
        type_line = d.get("type_line", "")

        if "Land" in type_line:
            produced = [c for c in d.get("produced_mana", []) if c in COLORS]
            lands.append((qty, name, produced))
        else:
            # Handle split/MDFC cards — take first face mana cost
            mc = d.get("mana_cost") or ""
            if not mc and "card_faces" in d:
                mc = d["card_faces"][0].get("mana_cost", "")
            parsed = _parse_mana_cost(mc)
            spells.append((qty, name, parsed["cmc"], parsed["pips"]))
            if name.lower() in CANTRIP_SAVINGS:
                auto_cantrip_adj += qty * CANTRIP_SAVINGS[name.lower()]
            # Non-land permanents that produce colored mana count as sources
            # (Mox Diamond, Birds of Paradise, Chrome Mox, etc.)
            # Exclude Instants and Sorceries (Dark Ritual is one-shot, not a permanent source)
            if "Instant" not in type_line and "Sorcery" not in type_line:
                produced = [c for c in d.get("produced_mana", []) if c in COLORS]
                if produced:
                    mana_perms.append((qty, name, produced))

    # Use manual cantrip count if toggle is on, otherwise use auto-detected
    if manual_cantrips:
        cantrip_adj = cantrip_manual_value * 0.28
    else:
        cantrip_adj = auto_cantrip_adj

    # ── Aggregate ─────────────────────────────────────────────────────────────
    total_lands = sum(q for q, _, _ in lands)
    sources: dict[str, int] = {c: 0 for c in COLORS}
    for qty, _, produced in lands:
        for c in produced:
            sources[c] += qty
    # Add mana-producing non-land permanents to colored sources
    for qty, _, produced in mana_perms:
        for c in produced:
            sources[c] += qty

    # Total mana sources = lands + mana permanents (Moxen etc. also pay generic mana)
    total_mana_sources = total_lands + sum(q for q, _, _ in mana_perms)

    spell_qty = sum(q for q, _, _, _ in spells)
    avg_cmc = sum(q * cmc for q, _, cmc, _ in spells) / spell_qty if spell_qty else 0

    recommended_raw = 19.59 + 1.90 * avg_cmc - cantrip_adj
    recommended = max(14, min(28, round(recommended_raw)))

    # ── KPI row ───────────────────────────────────────────────────────────────
    st.divider()
    k1, k2, k3, k4, k5 = st.columns(5)

    delta = total_lands - recommended
    if abs(delta) <= 1:
        land_color = THEME["success"]
        delta_str = f" (+{delta})" if delta > 0 else " (✓)"
    elif abs(delta) <= 2:
        land_color = THEME["warning"]
        delta_str = f" ({'+' if delta > 0 else ''}{delta})"
    else:
        land_color = THEME["danger"]
        delta_str = f" ({'+' if delta > 0 else ''}{delta})"

    with k1:
        st.markdown(html_kpi_card("Total Cards", str(sum(q for q, _ in raw_cards))), unsafe_allow_html=True)
    with k2:
        st.markdown(html_kpi_card("Lands in Deck", f"{total_lands}{delta_str}", color=land_color), unsafe_allow_html=True)
    with k3:
        st.markdown(html_kpi_card("Recommended Lands", str(recommended)), unsafe_allow_html=True)
    with k4:
        st.markdown(html_kpi_card("Avg CMC (spells)", f"{avg_cmc:.2f}"), unsafe_allow_html=True)
    cantrip_label = "Cantrip Savings (manual)" if manual_cantrips else "Cantrip Savings (auto)"
    with k5:
        st.markdown(html_kpi_card(cantrip_label, f"−{cantrip_adj:.1f} lands"), unsafe_allow_html=True)

    # ── Color source check ────────────────────────────────────────────────────
    used_colors = [c for c in COLORS if any(p.get(c, 0) >= 0.5 for _, _, _, p in spells)]

    if used_colors:
        st.markdown("### Color Source Check")
        caption = "Karsten minimums for 90% consistency on the play, 60 cards. Green = threshold met · Red = below threshold."
        if mana_perms:
            perm_names = ", ".join(f"{q}× {n}" for q, n, _ in mana_perms)
            caption += f"  ·  Sources include mana-producing permanents: {perm_names}."
        st.caption(caption)

        _bg     = THEME["surface"]
        _border = THEME["border"]
        _faint  = THEME["faint"]
        _muted  = THEME["muted"]
        _ok     = THEME["success"]
        _bad    = THEME["danger"]

        cols = st.columns(len(used_colors))
        for col, c in zip(cols, used_colors):
            actual = sources[c]
            relevant: set[tuple[int, int]] = set()
            for _, _, cmc, pips in spells:
                pip_f = pips.get(c, 0)
                if pip_f >= 0.5:
                    pip_i = min(3, max(1, int(math.ceil(pip_f))))
                    turn_i = min(4, max(1, int(cmc)))
                    relevant.add((pip_i, turn_i))

            with col:
                rows_html = ""
                for pip_i, turn_i in sorted(relevant):
                    needed = KARSTEN_SOURCES.get((pip_i, turn_i))
                    if needed is None:
                        continue
                    ok = actual >= needed
                    clr = _ok if ok else _bad
                    pips_imgs = "".join(mana_img(c, 16) for _ in range(pip_i))
                    icon = "✓" if ok else "✗"
                    rows_html += (
                        f"<div style='display:grid;grid-template-columns:18px 32px 1fr auto;"
                        f"align-items:center;gap:6px;padding:5px 0;"
                        f"border-bottom:1px solid {_border};'>"
                        # check icon
                        f"<span style='font-size:14px;color:{clr};font-weight:700;'>{icon}</span>"
                        # turn badge
                        f"<span style='font-size:11px;color:{_faint};font-family:monospace;"
                        f"background:{_border};border-radius:4px;padding:1px 5px;'>T{turn_i}</span>"
                        # pip symbols
                        f"<span style='display:flex;align-items:center;gap:2px;'>{pips_imgs}</span>"
                        # need / have
                        f"<span style='font-size:12px;white-space:nowrap;'>"
                        f"<span style='color:{_faint};'>need </span>"
                        f"<span style='color:{_muted};font-weight:600;'>{needed}</span>"
                        f"<span style='color:{_faint};'>  have </span>"
                        f"<span style='color:{clr};font-weight:700;'>{actual}</span>"
                        f"</span>"
                        f"</div>"
                    )

                sym = mana_img(c, 22)
                st.markdown(
                    f"<div style='background:{_bg};border:1px solid {_border};"
                    f"border-radius:8px;padding:14px 16px;'>"
                    f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:10px;'>"
                    f"{sym}"
                    f"<span style='font-size:13px;color:{_faint};'>{COLOR_NAMES[c]} sources</span>"
                    f"<span style='font-size:24px;font-weight:700;margin-left:auto;'>{actual}</span>"
                    f"</div>"
                    f"{rows_html}</div>",
                    unsafe_allow_html=True,
                )

    # ── Spell probability table ───────────────────────────────────────────────
    st.markdown("### Casting Probability on Curve")
    st.caption(
        f"P(can cast) on turn = CMC, {'on the draw' if on_draw else 'on the play'}. "
        f"Target: {target_pct}%."
    )

    _t   = THEME["text"]
    _mut = THEME["muted"]
    _fnt = THEME["faint"]
    _brd = THEME["border"]
    _sur = THEME["surface"]
    _bg2 = THEME["bg"]
    _tgt = target_pct / 100

    table_rows = ""
    for qty, name, cmc, pips in sorted(spells, key=lambda x: (x[2], x[1])):
        cmc_int = int(cmc)
        mc_html = mana_cost_html(pips, 15)

        if cmc == 0:
            table_rows += (
                f"<tr style='border-bottom:1px solid {_bg2};'>"
                f"<td style='padding:6px 10px;font-size:14px;'>{qty}× {name}</td>"
                f"<td style='padding:6px 10px;font-size:13px;color:{_mut};text-align:center;'>0</td>"
                f"<td style='padding:6px 10px;'>{mc_html}</td>"
                f"<td style='padding:6px 10px;font-size:14px;font-weight:600;"
                f"color:{THEME['success']};'>100%</td>"
                f"<td style='padding:6px 10px;font-size:13px;color:{_mut};'>—</td>"
                f"</tr>"
            )
            continue

        turn = max(1, cmc_int)
        cards_seen = min(7 + (turn if on_draw else turn - 1), int(deck_size))

        # Use total mana sources (lands + free mana permanents like Mox) for generic mana check
        land_prob = _hypergeom_at_least(int(deck_size), total_mana_sources, cards_seen, turn)

        color_probs: dict[str, float] = {}
        for c in COLORS:
            pip_f = pips.get(c, 0)
            if pip_f >= 0.5:
                pip_needed = max(1, int(math.ceil(pip_f)))
                color_probs[c] = _hypergeom_at_least(
                    int(deck_size), sources[c], cards_seen, pip_needed
                )

        combined = land_prob
        for p in color_probs.values():
            combined *= p

        # Color: green if on/above target, yellow if within 10pp below, red otherwise
        if combined >= _tgt:
            prob_color = THEME["success"]
        elif combined >= _tgt - 0.10:
            prob_color = THEME["warning"]
        else:
            prob_color = THEME["danger"]

        mana_label = "Mana sources" if mana_perms else "Lands"
        all_factors = {mana_label: land_prob, **{COLOR_NAMES[c]: p for c, p in color_probs.items()}}
        bottleneck = min(all_factors, key=all_factors.get)
        bottleneck_pct = all_factors[bottleneck]
        bottleneck_html = (
            f"<span style='color:{_mut};'>{bottleneck} ({bottleneck_pct:.1%})</span>"
            if combined < _tgt else "—"
        )

        table_rows += (
            f"<tr style='border-bottom:1px solid {_bg2};'>"
            f"<td style='padding:6px 10px;font-size:14px;'>{qty}× {name}</td>"
            f"<td style='padding:6px 10px;font-size:13px;color:{_mut};text-align:center;'>{cmc_int}</td>"
            f"<td style='padding:6px 10px;'>{mc_html}</td>"
            f"<td style='padding:6px 10px;font-size:15px;font-weight:700;color:{prob_color};'>"
            f"{combined:.1%}</td>"
            f"<td style='padding:6px 10px;font-size:13px;'>{bottleneck_html}</td>"
            f"</tr>"
        )

    if table_rows:
        headers = ["Card", "CMC", "Mana Cost", "P (on curve)", "Bottleneck"]
        header_html = "".join(
            f"<th style='padding:7px 10px;text-align:left;border-bottom:1px solid {_brd};"
            f"color:{_fnt};font-size:12px;font-weight:500;'>{h}</th>"
            for h in headers
        )
        st.markdown(
            f"<table style='width:100%;border-collapse:collapse;background:{_sur};"
            f"border-radius:8px;overflow:hidden;'>"
            f"<thead><tr>{header_html}</tr></thead>"
            f"<tbody>{table_rows}</tbody></table>",
            unsafe_allow_html=True,
        )

    # ── Methodology ───────────────────────────────────────────────────────────
    with st.expander("Methodology"):
        st.markdown(f"""
**Hypergeometric distribution** — correct model for sampling without replacement.

For each spell with CMC *N* cast on turn *N* ({('on draw: ' if on_draw else 'on play: ')}cards seen = 7 + {'N' if on_draw else 'N−1'}):

1. **Land drops**: P(draw ≥ N lands in first *cards_seen* cards)
2. **Color sources**: P(draw ≥ *k* sources of color C) for each required pip

Combined probability ≈ product of the above (treats color requirements as independent — slight underestimate for multi-color).

**Land recommendation**: `19.59 + 1.90 × avgCMC − cantrip_adjustment`
Frank Karsten 2022 regression. Cantrips: −{list(CANTRIP_SAVINGS.values())[0]} per copy for cheap draw spells.

**Source minimums** (Karsten, 90%, 60 cards, on the play):
T1 1-pip → 14  ·  T2 1-pip → 13  ·  T2 2-pip → 21  ·  T3 1-pip → 12  ·  T3 2-pip → 18  ·  T3 3-pip → 23
        """)


def _how_it_works():
    st.divider()
    st.markdown("#### How it works")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**1. Paste decklist**")
        st.caption("Standard `4 Card Name` format. Each card is looked up on Scryfall automatically to get mana cost and land color production.")
    with c2:
        st.markdown("**2. Hypergeometric math**")
        st.caption("For each spell, calculates P(have enough lands AND enough colored sources) by turn = CMC. Based on Frank Karsten's methodology.")
    with c3:
        st.markdown("**3. Karsten land formula**")
        st.caption("`19.59 + 1.90 × avgCMC` minus cantrip adjustment. Each Portent / Brainstorm / Opt in your list saves ~0.28 lands.")
