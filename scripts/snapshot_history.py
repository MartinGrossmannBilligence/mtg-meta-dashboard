import os
import json
import csv
from datetime import datetime

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
HISTORICAL_DIR = os.path.join(DATA_DIR, "historical_snapshots")

TIMEFRAMES_TO_SNAPSHOT = [
    {"folder": "1_month",  "source": "mtgdecks_matrix_1_month.json"},
    {"folder": "2_months", "source": "mtgdecks_matrix_2_months.json"},
    {"folder": "6_months", "source": "mtgdecks_matrix_6_months.json"}
]

def process_snapshot(timeframe_info):
    source_file = os.path.join(DATA_DIR, timeframe_info["source"])
    out_dir = os.path.join(HISTORICAL_DIR, timeframe_info["folder"])
    out_csv = os.path.join(out_dir, "historical_matchups.csv")

    if not os.path.exists(source_file):
        print(f"Source file not found for {timeframe_info['folder']}: {source_file}")
        return

    os.makedirs(out_dir, exist_ok=True)

    print(f"Reading metrics for {timeframe_info['folder']} from {source_file}...")
    with open(source_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    snapshot_date = datetime.now().strftime("%Y-%m-%d")
    file_exists = os.path.exists(out_csv)
    rows = []
    
    meta_shares = data.get("meta_shares", {})
    matrix = data.get("matrix", {})
    
    archetypes = set(list(meta_shares.keys()) + list(matrix.keys()))
    
    # Pre-calculate overall win rates
    overall_wr = {}
    for arch in archetypes:
        tw = 0
        tm = 0
        if arch in matrix:
            for opp, stats in matrix[arch].items():
                tw += stats.get("wins", 0)
                tm += stats.get("total_matches", 0)
        overall_wr[arch] = (tw / tm) if tm > 0 else 0.0

    # Build rows
    for arch in archetypes:
        share = meta_shares.get(arch, 0.0)
        arch_wr = overall_wr.get(arch, 0.0)
        
        if arch in matrix and matrix[arch]:
            for opp, stats in matrix[arch].items():
                rows.append({
                    "Date": snapshot_date,
                    "Archetype": arch,
                    "Archetype_Overall_WinRate": round(arch_wr, 4),
                    "Archetype_MetaShare": round(share, 4),
                    "Opponent": opp,
                    "Matchup_Wins": stats.get("wins", 0),
                    "Matchup_Losses": stats.get("losses", 0),
                    "Matchup_TotalMatches": stats.get("total_matches", 0),
                    "Matchup_WinRate": round(stats.get("win_rate", 0.0), 4)
                })
        else:
            if share > 0:
                rows.append({
                    "Date": snapshot_date, "Archetype": arch, "Archetype_Overall_WinRate": round(arch_wr, 4),
                    "Archetype_MetaShare": round(share, 4), "Opponent": "", "Matchup_Wins": 0,
                    "Matchup_Losses": 0, "Matchup_TotalMatches": 0, "Matchup_WinRate": 0.0
                })
                
    if not rows:
        print(f"No records found to snapshot for {timeframe_info['folder']}.")
        return
        
    fieldnames = [
        "Date", "Archetype", "Archetype_Overall_WinRate", "Archetype_MetaShare",
        "Opponent", "Matchup_Wins", "Matchup_Losses", "Matchup_TotalMatches", "Matchup_WinRate"
    ]
    with open(out_csv, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        
        for row in rows:
            writer.writerow(row)
            
    print(f"-> Appended {len(rows)} records to {out_csv}")

def run_snapshot():
    print(f"Starting multi-timeframe historical snapshot for {datetime.now().strftime('%Y-%m-%d')}...")
    for tf in TIMEFRAMES_TO_SNAPSHOT:
        process_snapshot(tf)
    print("Snapshot complete.")

if __name__ == "__main__":
    run_snapshot()
