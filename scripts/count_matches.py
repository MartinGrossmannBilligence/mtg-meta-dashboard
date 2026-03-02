import json
import os

def count_spicerack_matches(path):
    if not os.path.exists(path): return 0, 0
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    total_matches = 0
    for t in data:
        t_matches = 0
        for s in t.get('standings', []):
            t_matches += s.get('winsSwiss', 0) + s.get('lossesSwiss', 0) + s.get('draws', 0)
            t_matches += s.get('winsBracket', 0) + s.get('lossesBracket', 0)
        total_matches += t_matches / 2
    return len(data), int(total_matches)

def count_matrix_matches(path):
    if not os.path.exists(path): return 0
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    total_matches = 0
    matrix = data.get("matrix", {})
    if not matrix: return 0
    
    for archetype, targets in matrix.items():
        if isinstance(targets, dict):
            for t_data in targets.values():
                if isinstance(t_data, dict):
                    total_matches += t_data.get("total_matches", 0)
                elif isinstance(t_data, int):
                    total_matches += t_data
                elif isinstance(t_data, list):
                    total_matches += sum(t_data)
                    
    return int(total_matches / 2)

if __name__ == "__main__":
    t_count, s_matches = count_spicerack_matches('spicerack_dump.json')
    m_matches_6m = count_matrix_matches('data/mtgdecks_matrix_6_months.json')
    m_matches_1y = count_matrix_matches('data/mtgdecks_matrix_1_year.json')
    d_matches_6m = count_matrix_matches('data/archetype_matrix_6_months.json')
    d_matches_1y = count_matrix_matches('data/archetype_matrix_1_year.json')
    
    print(f"Spicerack (365 days): {t_count} tournaments, ~{s_matches} matches")
    print(f"MTGDecks (6 months): ~{m_matches_6m} matches")
    print(f"MTGDecks (1 year): ~{m_matches_1y} matches")
    print(f"Duress Crew (6 months): ~{d_matches_6m} matches")
    print(f"Duress Crew (1 year): ~{d_matches_1y} matches")
