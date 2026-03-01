# MTG Premodern Lab - Data Architecture

## Overview
This document describes the data flow, structure, and mapping logic of the MTG Premodern Lab application. The system integrates multiple data sources to provide a unified view of the Premodern metagame.

---

## ── 1. Data Sources & Extraction ──

The application relies on two primary data "layers":

### A. Local JSON/CSV Data (The "Duress" Layer)
*   **Source**: Manually collected or exported data from tournament spreadsheets (historic context).
*   **Files**: `archetype_matrix_[period].json`, `win_loss_records_[period].json`.
*   **Role**: Provides the baseline for older timeframes (1Y, 2Y, All Time) where MTGDecks data might be incomplete or differently structured.

### B. MTGDecks.net Data (The "Scrape" Layer)
*   **Source**: Automated extraction from MTGDecks.net.
*   **Extraction Scripts**:
    *   [`update_data_monthly.py`](file:///c:/Users/MartinGrossmann/Documents/Antigravity/mtg-meta-dashboard/scripts/update_data_monthly.py): Downloads matchup matrices and metagame shares for specific timeframes (30d, 60d, 90d, 180d, 1y, 2y). Handles historization and 90-day aggregation.
    *   [`scrape_decklists.py`](file:///c:/Users/MartinGrossmann/Documents/Antigravity/mtg-meta-dashboard/scripts/scrape_decklists.py): Scrapes the most recent competitive decklists for each archetype.
*   **Role**: Provides real-time tiering, metagame shares, and actual decklists.

---

## ── 2. Data Composition & Files ──

### 📂 `data/` Directory Structure

| File Pattern | Content Description |
| :--- | :--- |
| `mtgdecks_matrix_[period].json` | Contains `matrix` (matchup stats), `meta_shares`, and `tiers`. |
| `win_loss_records_[period].json` | Aggregated wins/losses per archetype for the specific timeframe. |
| `archetype_matrix_[period].json` | Matchup relationships from the "Duress" data source. |
| `decklists.json` | Stores the top 10 recent decklists for every archetype, including cards and "spiciness" score. |
| `historical_snapshots.csv` | Time-series data used for the trend visualizations. |

---

## ── 3. Data Mapping & Unification ──

The biggest challenge is that different sources use different names for the same archetype (e.g., "Mono Blue Dreadnought" vs "Stiflenought").

### The Mapping Logic ([mappings.py](file:///c:/Users/MartinGrossmann/Documents/Antigravity/mtg-meta-dashboard/src/mappings.py))
We use a central dictionary `DURESS_TO_MTGDECKS` to normalize all incoming data names to a single "source of truth".

**Key Mappings:**
*   `Mono Blue Dreadnought` → `Stiflenought`
*   `Blue/Black Psychatog` → `Psychatog`
*   `Sligh` → `Burn`
*   `Red/Green Oath Ponza` → `Oath Ponza`

### The Loading Pipeline ([analytics.py](file:///c:/Users/MartinGrossmann/Documents/Antigravity/mtg-meta-dashboard/src/analytics.py))
When the UI calls `load_period_data(data_dir, period)`:
1.  **Read Raw Files**: Loads both the Duress-style record and the MTGDecks-style matrix.
2.  **Normalize Names**: Applies the mapping dictionary to all archetype keys.
3.  **Aggregate Stats**: If multiple source archetypes map to one (e.g., Mono Blue & Blue/White Dreadnought), their wins and losses are summed into a single `Stiflenought` record.
4.  **Enrichment**: Overlays the `meta_shares` and `tiers` from MTGDecks onto the aggregated records.

---

## ── 4. Technical Workflows ──

### Monthly Update Lifecycle
Every month, the following happens (via `update_data_monthly.bat`):
1.  **Consolidated Update**: `update_data_monthly.py` handles fetching matrices for all periods (30d, 60d, 90d, 180d, 1y, 2y), calculating 90-day weights, and saving historical snapshots.
2.  **Update Decklists**: `scrape_decklists.py` refreshes the "Top Decklists" tab.
4.  **Fetch Icons**: `fetch_deck_icons.py` checks for new archetypes and downloads their art from Scryfall.

---

## ── 5. UI Integration ──

*   **Meta Overview**: Direct lookup into the unified `matrix` and `records`.
*   **Deck Analysis**: Filtered view focusing on a single archetype's relationships across all timeframes.
*   **Simulator**: Uses the weighted matchup matrix (`win_rate`) and current `meta_shares` to run Monte Carlo simulations.

---
*Last updated: 2026-02-27*
