# AI Context — MTG Premodern Lab Dashboard

This document explains the data architecture and key design decisions for any AI assistant working on this codebase.

---

## Data Sources

There are **two separate data providers** with different strengths:

### 1. Duress Crew (`data.duresscrew.com`)
- Source of **win/loss records** and **matchup matrix** for long-term timeframes.
- Data files: `archetype_matrix_{period}.json`, `win_loss_records_{period}.json`
- Periods: `1_year`, `2_years`, `6_months`, `3_months`
- **Does NOT contain `meta_shares`** — the archetype matrix JSON from Duress has no metagame share data.
- Deck names use Duress Crew naming conventions (mapped to MTGDecks names via `src/mappings.py → DURESS_TO_MTGDECKS`).

### 2. MTGDecks.net (`mtgdecks.net`)
- Source of **meta shares** (how often a deck appears in the field) and **match matrices** for shorter timeframes.
- Data files: `mtgdecks_matrix_{period}.json`
- Periods: `all_time`, `1_year`, `6_months`, `2_months`, `1_month`
- All files contain `meta_shares` key: `{"DeckName": 0.0802, ...}` (values are fractions 0–1).
- Deck names use MTGDecks naming convention.

---

## Timeframe Mapping (CRITICAL)

The sidebar `TIMEFRAMES` dict in `app.py` maps display names → internal data keys:

| Display Name | Internal Key           | Win Rate Source      | Meta Share Source              |
|-------------|------------------------|----------------------|-------------------------------|
| All Time    | `all_time`             | Duress `archetype_matrix_all_time.json` | MTGDecks `mtgdecks_matrix_all_time.json` |
| 1 Year      | `1_year`               | Duress `archetype_matrix_1_year.json`   | MTGDecks `mtgdecks_matrix_1_year.json`   |
| 6 Months    | `mtgdecks_matrix_6_months` | MTGDecks (matrix embedded) | MTGDecks (embedded in same file) |
| 2 Months    | `mtgdecks_matrix_2_months` | MTGDecks (matrix embedded) | MTGDecks (embedded in same file) |

**Key rule:** If the internal key starts with `mtgdecks_matrix_`, the data comes entirely from MTGDecks (including meta shares). If it's just a plain period name like `all_time` or `1_year`, it's Duress data for win rates + MTGDecks data injected for meta shares.

---

## `load_period_data(data_dir, period)` — `src/analytics.py`

Central function. Behavior:
- **If `period.startswith("mtgdecks_matrix")`**: loads the single MTGDecks file, computes records from the embedded matrix, returns `matrix_data` (which already has `meta_shares`).
- **Otherwise** (Duress period): loads `archetype_matrix_{period}.json` + `win_loss_records_{period}.json`, applies `DURESS_TO_MTGDECKS` name mapping, then **overrides `meta_shares`** by loading the corresponding MTGDecks file:
  - `1_year` → reads `mtgdecks_matrix_1_year.json`
  - `all_time` → reads `mtgdecks_matrix_all_time.json`

---

## `matrix_data` object structure

```python
{
  "archetypes": ["Burn", "Goblins", ...],      # list of deck names
  "tiers": {"Burn": "Tier 1", ...},             # tier assignments (MTGDecks only)
  "matrix": {
    "Burn": {
      "Goblins": {"wins": 50, "losses": 40, "draws": 2, "total_matches": 92, "win_rate": 0.543}
    }
  },
  "meta_shares": {"Burn": 0.0802, "Goblins": 0.0705, ...}   # fraction of field (0–1)
}
```

---

## Deck Name Mapping

`src/mappings.py` contains `DURESS_TO_MTGDECKS` dict. It maps Duress Crew deck names → MTGDecks deck names. Applied in `load_period_data` for Duress periods.

---

## Local Deck Icons

- Stored in `assets/deck_icons/{slug}.jpg` (art_crop from Scryfall)
- Slug: `deck_name.lower().replace(" ", "_").replace("/", "_").replace("'", "")`
- Fetched via `scripts/fetch_deck_icons.py`
- Loaded as base64 via `src/ui.py → get_icon_b64(deck_name, data_dir)`
- Used in: HTML tables (via `html_deck_table`), and the Meta Share vs Win Rate scatter plot.

---

## Pages

- **`src/pages/meta_overview.py`** — `show_meta_overview()`: Metagame Stats tab + Matchup Matrix tab.
  - Uses `meta_shares` from `matrix_dict.get("meta_shares", {})` for the scatter plot and "Meta Share" column.
  - Scatter plot: X = meta share, Y = win rate, icons = local deck jpegs.
  - Default deck selection = all Tier 1 decks from `tiers_dict`.
- **`src/pages/analysis.py`** — `show_analysis()`: Deck-specific analysis with matchup breakdown.
- **`src/pages/simulator.py`** — `show_simulator()`: Tournament EV simulator.

---

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/update_data_monthly.py` | Main ingestion script for MTGDecks win rates and meta shares |
| `scripts/scrape_decklists.py` | Scrapes top decklists and card data |
| `scripts/fetch_deck_icons.py` | Downloads art_crop JPEG icons per deck from Scryfall |
| `scripts/encode_mana_json.py` | Encodes mana symbol SVGs to base64 for inline use |
