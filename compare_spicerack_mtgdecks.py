import json
import urllib.request

def get_spicerack_data(days):
    url = f"https://api.spicerack.gg/api/export-decklists/?event_format=Premodern&num_days={days}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def analyze_spicerack(data):
    tournaments = len(data)
    players = 0
    matches = 0
    archetypes = set()
    for t in data:
        players += t.get('players', 0)
        for s in t.get('standings', []):
            matches += s.get('winsSwiss', 0) + s.get('lossesSwiss', 0) + s.get('draws', 0)
            matches += s.get('winsBracket', 0) + s.get('lossesBracket', 0)
            arch = s.get('archetype', {}).get('name')
            if arch: archetypes.add(arch)
    return tournaments, players, matches // 2, len(archetypes)

def analyze_mtgdecks(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    matrix = data.get('matrix', {})
    total_matches = 0
    for row in matrix.values():
        for col in row.values():
            total_matches += col.get('total_matches', 0)
    return len(data.get('archetypes', [])), total_matches // 2

# Analyze Spicerack 30 days
print("Fetching Spicerack data (30 days)...")
spice_f = get_spicerack_data(30)
st, sp, sm, sa = analyze_spicerack(spice_f)

# Analyze MTGDecks 30 days
print("Analyzing MTGDecks local data (30 days)...")
ma, mm = analyze_mtgdecks('data/mtgdecks_matrix_30_days.json')

print("\n--- 30 Day Comparison ---")
print(f"{'Metric':<15} | {'Spicerack':<15} | {'MTGDecks':<15}")
print("-" * 50)
print(f"{'Tournaments':<15} | {st:<15} | {'N/A':<15}")
print(f"{'Archetypes':<15} | {sa:<15} | {ma:<15}")
print(f"{'Total Players':<15} | {sp:<15} | {'N/A':<15}")
print(f"{'Total Matches':<15} | {sm:<15} | {mm:<15}")

# Quick check on larger Spicerack window
print("\n--- Spicerack Extended Windows ---")
for d in [60, 90, 180, 365]:
    st, sp, sm, sa = analyze_spicerack(get_spicerack_data(d))
    print(f"{d:>3} Days: Tournaments={st:<3}, Players={sp:<4}, Matches={sm:<4}, Archetypes={sa}")

# Compare with Duress crew 180 days (6 months)
ma6, mm6 = analyze_mtgdecks('data/archetype_matrix_6_months.json')
print(f"\nMTGDecks (Duress) 180 Days (6 Months): Archetypes={ma6}, Matches={mm6}")

# Compare with Duress crew 1 Year
ma1y, mm1y = analyze_mtgdecks('data/archetype_matrix_1_year.json')
print(f"MTGDecks (Duress) 1 Year: Archetypes={ma1y}, Matches={mm1y}")
