import pandas as pd
import numpy as np
import json
import os
from scipy.stats import norm

def load_period_data(data_dir, period):
    if period.startswith("mtgdecks_matrix"):
        matrix_path = os.path.join(data_dir, f"{period}.json")
        with open(matrix_path, 'r', encoding='utf-8') as f:
            matrix_data = json.load(f)
            
        records_data = []
        for arch, matchups in matrix_data.get("matrix", {}).items():
            wins, losses, draws, matches = 0, 0, 0, 0
            for opp, stats in matchups.items():
                wins += stats.get("wins", 0)
                losses += stats.get("losses", 0)
                matches += stats.get("total_matches", 0)
            if matches > 0:
                records_data.append({
                    "archetype": arch,
                    "wins": wins,
                    "losses": losses,
                    "draws": draws,
                    "total_matches": matches,
                    "win_rate": wins / matches
                })
        return matrix_data, records_data
    matrix_path = os.path.join(data_dir, f"archetype_matrix_{period}.json")
    records_path = os.path.join(data_dir, f"win_loss_records_{period}.json")
    
    with open(matrix_path, 'r', encoding='utf-8') as f:
        matrix_data = json.load(f)
    
    with open(records_path, 'r', encoding='utf-8') as f:
        records_data = json.load(f)
        
    # Apply DURESS_TO_MTGDECKS mapping for local duress files
    from src.mappings import DURESS_TO_MTGDECKS
    import copy
    
    mapped_archetypes = []
    for a in matrix_data.get('archetypes', []):
        mapped_archetypes.append(DURESS_TO_MTGDECKS.get(a, a))
    matrix_data['archetypes'] = sorted(list(set(mapped_archetypes)))
    
    mapped_matrix = {}
    for old_arch, opps in matrix_data.get('matrix', {}).items():
        new_arch = DURESS_TO_MTGDECKS.get(old_arch, old_arch)
        if new_arch not in mapped_matrix: mapped_matrix[new_arch] = {}
        
        for old_opp, stats in opps.items():
            new_opp = DURESS_TO_MTGDECKS.get(old_opp, old_opp)
            
            # Combine stats if multiple old map to same new
            if new_opp not in mapped_matrix[new_arch]:
                new_stats = copy.deepcopy(stats)
                new_stats['archetype'] = new_opp
                mapped_matrix[new_arch][new_opp] = new_stats
            else:
                existing = mapped_matrix[new_arch][new_opp]
                existing['wins'] += stats.get('wins', 0)
                existing['losses'] += stats.get('losses', 0)
                existing['draws'] += stats.get('draws', 0)
                existing['total_matches'] += stats.get('total_matches', 0)
                if existing['total_matches'] > 0:
                    existing['win_rate'] = (existing['wins'] + existing['draws']*0.5) / existing['total_matches']
                    
    matrix_data['matrix'] = mapped_matrix
    
    # Merge records that map to the same new archetype name
    merged_records = {}
    for rec in records_data:
        new_name = DURESS_TO_MTGDECKS.get(rec.get('archetype'), rec.get('archetype'))
        if new_name in merged_records:
            merged_records[new_name]['wins'] += rec.get('wins', 0)
            merged_records[new_name]['losses'] += rec.get('losses', 0)
            merged_records[new_name]['draws'] += rec.get('draws', 0)
            merged_records[new_name]['total_matches'] += rec.get('total_matches', 0)
            t = merged_records[new_name]['total_matches']
            if t > 0:
                merged_records[new_name]['win_rate'] = (merged_records[new_name]['wins'] + merged_records[new_name]['draws'] * 0.5) / t
        else:
            merged_records[new_name] = dict(rec)
            merged_records[new_name]['archetype'] = new_name
    records_data = list(merged_records.values())

    # Override meta shares and tiers using mtgdecks data for relevant periods
    # as mtgdecks better reflects the actual metagame share and contains tiers.
    mtgdecks_path = os.path.join(data_dir, f"mtgdecks_matrix_{period}.json")
        
    if os.path.exists(mtgdecks_path):
        with open(mtgdecks_path, 'r', encoding='utf-8') as mf:
            mtg_data = json.load(mf)
            if "meta_shares" in mtg_data:
                # Normalize keys to uppercase for better matching if needed, 
                # but preserve original for the app's lookup logic
                matrix_data["meta_shares"] = mtg_data["meta_shares"]
            if "tiers" in mtg_data:
                matrix_data["tiers"] = mtg_data["tiers"]

    return matrix_data, records_data

def wilson_score_interval(wins, total, confidence=0.95):
    """Calculate the Wilson score interval for a binomial proportion."""
    if total == 0:
        return 0, 0
    
    z = norm.ppf(1 - (1 - confidence) / 2)
    p = wins / total
    
    denom = 1 + z**2 / total
    centre_adj = p + z**2 / (2 * total)
    adj_error = z * np.sqrt(p * (1 - p) / total + z**2 / (4 * total**2))
    
    lower = (centre_adj - adj_error) / denom
    upper = (centre_adj + adj_error) / denom
    
    return lower, upper

def get_matchup_stats(matrix_dict, arch1, arch2):
    """Get stats for a specific matchup."""
    row = matrix_dict.get(arch1, {})
    cell = row.get(arch2, {})
    return cell

def calculate_polarity(archetype_name, matrix_dict, all_archetypes):
    """
    Calculate deck polarity: standard deviation of win rates across matchups.
    Excludes self-matchups and matchups with very low sample size.
    """
    win_rates = []
    row_data = matrix_dict.get(archetype_name, {})
    
    for other in all_archetypes:
        if other == archetype_name:
            continue
        
        cell = row_data.get(other, {})
        total = cell.get("total_matches", 0)
        if total >= 5: # Minimum threshold for polarity analysis
            win_rates.append(cell.get("win_rate", 0))
            
    if not win_rates:
        return 0
    
    return np.std(win_rates)

def calculate_expected_winrate(meta_shares, matrix_dict, all_archetypes):
    """
    Calculate target deck winrates based on expected field composition.
    meta_shares: dict {archetype: share_percentage (0-1)}
    """
    ev_results = {}
    
    for target in all_archetypes:
        expected_wr = 0
        total_share = 0
        
        for opponent, share in meta_shares.items():
            if share <= 0:
                continue
                
            cell = matrix_dict.get(target, {}).get(opponent, {})
            wr = cell.get("win_rate", 0.5) # Default to 50% if no data
            expected_wr += wr * share
            total_share += share
            
        if total_share > 0:
            ev_results[target] = expected_wr / total_share
            
    return ev_results

def get_period_comparison(data_dir, periods_dict):
    """
    Compare all archetypes across different timeframes.
    Returns a DataFrame with win rates per period.
    """
    all_data = []
    
    for display_name, internal_key in periods_dict.items():
        try:
            _, records = load_period_data(data_dir, internal_key)
            for rec in records:
                all_data.append({
                    "Archetype": rec["archetype"],
                    "Period": display_name,
                    "Win Rate": rec.get("win_rate", 0),
                    "Games": rec.get("total_matches", 0)
                })
        except Exception as e:
            print(f"Error loading {internal_key}: {e}")
            
    df = pd.DataFrame(all_data)
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
        
    # Due to archetype mapping, we might have multiple entries for the same Archetype + Period.
    # We must aggregate them (e.g., sum games, weighted average for win rate).
    
    # Calculate total wins to accurately average win_rate
    df["Wins"] = df["Win Rate"] * df["Games"]
    
    grouped = df.groupby(["Archetype", "Period"]).agg({
        "Games": "sum",
        "Wins": "sum"
    }).reset_index()
    
    grouped["Win Rate"] = grouped["Wins"] / grouped["Games"]
    grouped["Win Rate"] = grouped["Win Rate"].fillna(0)
    
    pivot_df = grouped.pivot(index="Archetype", columns="Period", values="Win Rate")
    games_df = grouped.pivot(index="Archetype", columns="Period", values="Games").fillna(0)
    
    return pivot_df, games_df

# Mapping of Archetypes to Defining Cards for Visuals
DECK_CARD_MAP = {
    "Stasis": "Stasis",
    "Goblins": "Goblin Lackey",
    "Sligh": "Jackal Pup",
    "Survival": "Survival of the Fittest",
    "The Deck": "Jayemdae Tome",
    "Landstill": "Standstill",
    "Pox": "Pox",
    "Psychatog": "Psychatog",
    "Madness": "Arrogant Wurm",
    "Reanimator": "Exhume",
    "Storm": "Tendrils of Agony",
    "Dredge": "Golgari Grave-Troll",
    "Elves": "Heritage Druid",
    "Burn": "Lightning Bolt",
    "Delver": "Delver of Secrets",
    "Death & Taxes": "Thalia, Guardian of Thraben",
    "Miracles": "Terminus",
    "Infect": "Glistener Elf",
    "Merfolk": "Lord of Atlantis",
    "Zoo": "Wild Nacatl",
    "Control": "Counterspell",
    "Aggro": "Tarmogoyf",
    "Combo": "Dark Ritual",
    "High Tide": "High Tide",
    "Replenish": "Replenish",
    "Tinker": "Tinker",
    "Suicide Black": "Carnophage",
    "White Weenie": "Savannah Lions"
}

def get_card_image_url(archetype_name):
    """Get the Scryfall image URL for a defining card of the archetype."""
    card_name = DECK_CARD_MAP.get(archetype_name, archetype_name)
    # Using Scryfall's direct image API: https://scryfall.com/docs/api/cards/named?format=image
    # We use format=image and version=normal
    import urllib.parse
    encoded_name = urllib.parse.quote(card_name)
    return f"https://api.scryfall.com/cards/named?exact={encoded_name}&format=image&version=normal"
