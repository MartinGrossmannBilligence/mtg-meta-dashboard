import json
import urllib.request
import os

def get_spicerack_data(days):
    url = f"https://api.spicerack.gg/api/export-decklists/?event_format=Premodern&num_days={days}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"Error fetching Spicerack ({days} days): {e}")
        return []

def analyze_spicerack(data):
    tournaments = len(data)
    players = 0
    matches = 0
    for t in data:
        players += t.get('players', 0)
        for s in t.get('standings', []):
            matches += s.get('winsSwiss', 0) + s.get('lossesSwiss', 0) + s.get('draws', 0)
            matches += s.get('winsBracket', 0) + s.get('lossesBracket', 0)
    return tournaments, players, matches // 2

def analyze_mtgdecks(file_path):
    if not os.path.exists(file_path):
        return 0, 0
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        matrix = data.get('matrix', {})
        total_matches = 0
        for row in matrix.values():
            for col in row.values():
                total_matches += col.get('total_matches', 0)
        return len(data.get('archetypes', [])), total_matches // 2
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
        return 0, 0

print("Analyzing data...")

# Spicerack Windows
spice_30 = analyze_spicerack(get_spicerack_data(30))
spice_60 = analyze_spicerack(get_spicerack_data(60))
spice_180 = analyze_spicerack(get_spicerack_data(180))
spice_365 = analyze_spicerack(get_spicerack_data(365))

# MTGDecks Windows
mtg_30 = analyze_mtgdecks('data/mtgdecks_matrix_30_days.json')
mtg_60 = analyze_mtgdecks('data/mtgdecks_matrix_60_days.json')
mtg_180 = analyze_mtgdecks('data/mtgdecks_matrix_180_days.json')
mtg_365 = analyze_mtgdecks('data/mtgdecks_matrix_1_year.json')

# Duress Crew Windows
dur_180 = analyze_mtgdecks('data/archetype_matrix_6_months.json')
dur_365 = analyze_mtgdecks('data/archetype_matrix_1_year.json')

results = [
    ("30 Days", spice_30[2], mtg_30[1], 0),
    ("60 Days", spice_60[2], mtg_60[1], 0),
    ("180 Days", spice_180[2], mtg_180[1], dur_180[1]),
    ("365 Days", spice_365[2], mtg_365[1], dur_365[1])
]

print("\n--- Detailed Multi-Window Comparison (Total Matches) ---")
print(f"{'Window':<15} | {'Spicerack':<15} | {'MTGDecks':<15} | {'Duress Crew':<15}")
print("-" * 65)
for window, s, m, d in results:
    print(f"{window:<15} | {s:<15} | {m:<15} | {d:<15}")
