import json
from bs4 import BeautifulSoup
import re

print('\n--- Winrates Comparison ---')
with open('winrates_debug.html', 'r', encoding='utf-8') as f:
    text = BeautifulSoup(f.read(), 'html.parser').get_text()

matches_mtgdecks_texts = re.findall(r'\((\d+)\s+matches\)', text, re.IGNORECASE)
total_matches_mtgdecks = sum(int(m) for m in matches_mtgdecks_texts)

# Wait mtgdecks table matches might be symmetric. The text says "(X matches)" in cells. 
# Usually a symmetric table means each match is in two cells, so we divide by 2.
print(f'Mtgdecks total matches string sum: {total_matches_mtgdecks // 2} (assuming symmetric table)')

# Just parsing mtgdecks top right KPI if it exists:
overall = re.search(r'based on (\d+) matches', text, re.IGNORECASE)
if overall:
    print(f'Mtgdecks explicitly claims: {overall.group(1)} matches')

with open('data/archetype_matrix_all_time.json', 'r', encoding='utf-8') as f:
    duress_data = json.load(f)
    print(f'Archetypes in Duress: {len(duress_data["archetypes"])}')
    total_duress = sum([sum([c.get("total_matches", 0) for c in r.values()]) for r in duress_data["matrix"].values()]) // 2
    print(f'Total matches in Duress Crew (2 Years): {total_duress}')

with open('data/archetype_matrix_6_months.json', 'r', encoding='utf-8') as f:
    duress_data_6 = json.load(f)
    print(f'Total matches in Duress Crew (6 Months): {sum([sum([c.get("total_matches", 0) for c in r.values()]) for r in duress_data_6["matrix"].values()]) // 2}')

with open('data/archetype_matrix_1_year.json', 'r', encoding='utf-8') as f:
    duress_data_1 = json.load(f)
    print(f'Total matches in Duress Crew (1 Year): {sum([sum([c.get("total_matches", 0) for c in r.values()]) for r in duress_data_1["matrix"].values()]) // 2}')
