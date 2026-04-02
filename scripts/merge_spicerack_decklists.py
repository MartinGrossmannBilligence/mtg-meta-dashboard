import json
import os
from datetime import datetime

DECKLISTS_FILE = 'data/decklists.json'
SPICERACK_FILE = 'data/spicerack_mapped.json'

def format_date(timestamp):
    # Spicerack uses Unix timestamps. Target: "15-Aug-2025"
    if not timestamp: return ""
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%d-%b-%Y")

def merge():
    if not os.path.exists(SPICERACK_FILE):
        print(f"Error: {SPICERACK_FILE} not found.")
        return

    with open(SPICERACK_FILE, 'r', encoding='utf-8') as f:
        spicerack_tournaments = json.load(f)

    if os.path.exists(DECKLISTS_FILE):
        with open(DECKLISTS_FILE, 'r', encoding='utf-8') as f:
            decklists_data = json.load(f)
    else:
        decklists_data = {}

    # Track URLs to prevent duplicates
    existing_urls = set()
    for archetype, decks in decklists_data.items():
        for d in decks:
            if d.get("url"):
                existing_urls.add(d["url"])

    added_count = 0
    for tournament in spicerack_tournaments:
        t_name = tournament.get("tournamentName")
        t_date = format_date(tournament.get("startDate"))
        t_players = tournament.get("players", 0)
        
        for standing in tournament.get("standings", []):
            mapped_arch = standing.get("mapped_archetype")
            deck_data = standing.get("deck_data")
            
            if not mapped_arch or mapped_arch == "Unknown" or not deck_data:
                continue
                
            url = deck_data.get("url")
            if url in existing_urls:
                continue
            
            # Format cards
            cards = []
            for c in deck_data.get("mainboard", []):
                cards.append({
                    "qty": c["qty"],
                    "name": c["name"],
                    "section": "Maindeck",
                    "type": c.get("type", "Other")
                })
            for c in deck_data.get("sideboard", []):
                cards.append({
                    "qty": c["qty"],
                    "name": c["name"],
                    "section": "Sideboard",
                    "type": c.get("type", "Other")
                })
                
            new_deck = {
                "player": standing.get("name", "Unknown"),
                "rank": "N/A", # Spicerack standings don't always have rank field, use name sequence or skip
                "players": t_players,
                "event": t_name,
                "date": t_date,
                "url": url,
                "colors": [], # We could calculate this from cards, but leaving empty for now
                "spice": 0,
                "cards": cards
            }
            
            if mapped_arch not in decklists_data:
                decklists_data[mapped_arch] = []
            
            decklists_data[mapped_arch].append(new_deck)
            existing_urls.add(url)
            added_count += 1

    # Sort each archetype by date (newest first)
    for arch in decklists_data:
        try:
            # Clean date string (MTGDecks: "15-Aug -2025" -> "15-Aug-2025")
            def parse_date(date_str):
                if not date_str: return datetime.min
                clean_date = date_str.replace(" ", "")
                return datetime.strptime(clean_date, "%d-%b-%Y")

            decklists_data[arch].sort(
                key=lambda x: parse_date(x.get("date", "")),
                reverse=True
            )
            # Limit to top 20
            decklists_data[arch] = decklists_data[arch][:20]
        except Exception as e:
            print(f"Warning: Failed to sort/trim {arch}: {e}")
            # Still attempt to trim even if sort fails
            decklists_data[arch] = decklists_data[arch][:20]

    with open(DECKLISTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(decklists_data, f, indent=2)

    print(f"Merge complete! Added {added_count} new decklists from Spicerack.")

if __name__ == "__main__":
    merge()
