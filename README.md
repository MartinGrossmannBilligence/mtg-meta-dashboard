# Premodern Meta Lab

Interactive metagame analytics dashboard for **Premodern Magic: The Gathering** — built on data from Duress Crew.

🔗 **Live app:** [premodern-meta-lab.streamlit.app](https://premodern-meta-lab.streamlit.app)

## Features

- **Deck Analysis** — Deep-dive into any archetype: overall win rate, polarity index, matchup distribution chart, Top 5 best/worst matchups, full matchup table with Wilson confidence intervals + sample quality badges, and win rate history across time windows.
- **Meta Overview** — Full metagame stats table + interactive matchup heatmap matrix + win rate trends across time periods.
- **Tournament Simulator** — Projected win rate calculator based on custom field compositions.

## Data Source

All metagame data is provided by [Duress Crew](https://data.duresscrew.com/).

## How to Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deployment

Hosted on [Streamlit Cloud](https://streamlit.io/cloud). Pushes to `main` deploy automatically.
