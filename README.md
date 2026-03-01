# Premodern Meta Lab

Interactive metagame analytics dashboard for **Premodern Magic: The Gathering** — built on data from Duress Crew.

🔗 **Live app:** [premodern-meta-lab.streamlit.app](https://premodern-meta-lab.streamlit.app)

## Features

- **Deck Analysis** — Deep-dive into any archetype: overall win rate, polarity index, matchup distribution chart, Top 5 best/worst matchups, full matchup table with Wilson confidence intervals + sample quality badges, and win rate history across time windows.
- **Meta Overview** — Full metagame stats table + interactive matchup heatmap matrix (defaulting to the top 22 user-defined decks) + win rate trends across time periods. Custom tooltips displaying cleanly formatted values.
- **Tournament Simulator** — Projected win rate calculator based on custom field compositions. Automatically pre-fills expected deck shares dynamically based on the real Meta Share from the selected timeframe.

## Data Source

Primary metagame data and decklists are fetched from [MTGDecks.net](https://mtgdecks.net/Premodern), integrated with historic data from [Duress Crew](https://data.duresscrew.com/).

## Technical Documentation

For details on data flow, archetype mapping, and automation scripts, see [DATA_ARCHITECTURE.md](file:///c:/Users/MartinGrossmann/Documents/Antigravity/mtg-meta-dashboard/DATA_ARCHITECTURE.md).

## How to Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deployment

Hosted on [Streamlit Cloud](https://streamlit.io/cloud). Pushes to `main` deploy automatically.
