import json
import os

SPICERACK_MAPPED = 'data/spicerack_mapped.json'
OUTPUT_RECORDS = 'data/win_loss_records_spicerack_365.json'
OUTPUT_MATRIX = 'data/archetype_matrix_spicerack_365.json'

def convert():
    if not os.path.exists(SPICERACK_MAPPED):
        print(f"Error: {SPICERACK_MAPPED} not found. Run integrator first.")
        return

    with open(SPICERACK_MAPPED, 'r', encoding='utf-8') as f:
        tournaments = json.load(f)

    archetype_stats = {}
    # matrix structure: attacker -> defender -> {wins, losses, draws, total_matches}
    matrix = {}

    for t in tournaments:
        standings = t.get('standings', [])
        
        # We need to reasonably infer matchups from Spicerack standings.
        # Since Spicerack doesn't give a round-by-round breakdown in the export,
        # we'll use the aggregated Swiss + Bracket counts for overall Win Rate.
        # Mirroring 'Duress' style record structure.
        
        for s in standings:
            arch = s.get('mapped_archetype')
            if not arch or arch == "Unknown":
                continue
            
            if arch not in archetype_stats:
                archetype_stats[arch] = {"wins": 0, "losses": 0, "draws": 0, "total_matches": 0}
            
            w = s.get('winsSwiss', 0) + s.get('winsBracket', 0)
            l = s.get('lossesSwiss', 0) + s.get('lossesBracket', 0)
            d = s.get('draws', 0)
            
            archetype_stats[arch]["wins"] += w
            archetype_stats[arch]["losses"] += l
            archetype_stats[arch]["draws"] += d
            archetype_stats[arch]["total_matches"] += (w + l + d)

    # Convert to records list
    records = []
    for arch, stats in archetype_stats.items():
        if stats["total_matches"] > 0:
            stats["archetype"] = arch
            stats["win_rate"] = (stats["wins"] + stats["draws"]*0.5) / stats["total_matches"]
            records.append(stats)
    
    # Sort by matches desc
    records.sort(key=lambda x: x["total_matches"], reverse=True)

    # Save Records
    with open(OUTPUT_RECORDS, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=2)

    # Save a dummy matrix (Spicerack export doesn't have vs_archetype data yet)
    # This allows the app to load it without crashing
    matrix_output = {
        "time_frame": "Spicerack 365D",
        "archetypes": sorted(list(archetype_stats.keys())),
        "matrix": {}
    }
    with open(OUTPUT_MATRIX, 'w', encoding='utf-8') as f:
        json.dump(matrix_output, f, indent=2)

    print(f"Conversion complete!")
    print(f"Stats saved to {OUTPUT_RECORDS}")
    print(f"Dummy matrix saved to {OUTPUT_MATRIX} (required for dashboard loader)")

if __name__ == "__main__":
    convert()
