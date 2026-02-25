import os
import json
import csv
from datetime import datetime

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
SOURCE_MATRIX = os.path.join(DATA_DIR, "mtgdecks_matrix_1_month.json")
OUTPUT_CSV = os.path.join(DATA_DIR, "historical_snapshots.csv")

def run_snapshot():
    if not os.path.exists(SOURCE_MATRIX):
        print(f"Source file not found: {SOURCE_MATRIX}")
        return

    print(f"Reading current metrics from {SOURCE_MATRIX}...")
    with open(SOURCE_MATRIX, "r", encoding="utf-8") as f:
        data = json.load(f)

    snapshot_date = datetime.now().strftime("%Y-%m-%d")
    
    # Check if CSV exists and write header if not
    file_exists = os.path.exists(OUTPUT_CSV)
    
    rows = []
    
    meta_shares = data.get("meta_shares", {})
    matrix = data.get("matrix", {})
    
    # We need to iterate over all archetypes and calculate their total win rate
    # by summing up all their matchups in the matrix.
    archetypes = set(list(meta_shares.keys()) + list(matrix.keys()))
    
    for arch in archetypes:
        share = meta_shares.get(arch, 0.0)
        
        # Calculate overall win rate
        total_wins = 0
        total_matches = 0
        
        if arch in matrix:
            for opp, stats in matrix[arch].items():
                total_wins += stats.get("wins", 0)
                total_matches += stats.get("total_matches", 0)
                
        # If no matches, win rate is just 0
        win_rate = (total_wins / total_matches) if total_matches > 0 else 0.0
        
        # Only log archetypes with meaningful data
        if total_matches > 0 or share > 0:
            rows.append({
                "Date": snapshot_date,
                "Archetype": arch,
                "WinRate": round(win_rate, 4),
                "MetaShare": round(share, 4),
                "TotalMatches": total_matches
            })
            
    if not rows:
        print("No records found to snapshot.")
        return
        
    # Append to CSV
    with open(OUTPUT_CSV, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Date", "Archetype", "WinRate", "MetaShare", "TotalMatches"])
        if not file_exists:
            writer.writeheader()
        
        for row in rows:
            writer.writerow(row)
            
    print(f"Successfully appended {len(rows)} archetype records to {OUTPUT_CSV} for date {snapshot_date}.")

if __name__ == "__main__":
    run_snapshot()
