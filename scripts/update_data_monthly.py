import json
import re
import os
import shutil
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

from playwright.sync_api import sync_playwright

# --- Configuration ---
# Heads up: Playwright manages these automatically, some aren't needed but kept for structural purity.

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
HISTORICAL_DIR = os.path.join(DATA_DIR, 'historical')

# Sources definition
# (Timeframe Label, Winrate Path, Metagame Path)
# None for Winrate Path means skip WR for that timeframe
SOURCES = [
    ("30_days", "range:last30days", "metagame:last-month"),
    ("60_days", "range:last60days", "metagame:last-2-months"),
    ("180_days", "range:last180days", "metagame:last-6-months")
]

# --- Helper Functions ---

def fetch_html(url, page):
    print(f"Fetching: {url}")
    try:
        page.goto(url)
        # Wait up to 60 seconds for a table to appear to give time to manually clear Cloudflare if needed
        try:
            page.wait_for_selector('table', timeout=60000)
        except Exception:
            print(f"Warning: Cloudflare timeout or no table found at {url}. Proceeding anyway...")
        return page.content()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def get_tiers(page):
    print("Fetching tiers from MTGDecks...")
    html = fetch_html('https://mtgdecks.net/Premodern', page)
    if not html: return {}
    
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', id='allArchetypes')
    if not table: return {}
    
    tier_mapping = {}
    for row in table.find_all('tr'):
        classes = row.get('class', [])
        tier = next((c for c in classes if c.startswith('tier-') and c != 'tier-all'), 'tier-unknown')
        if tier != 'tier-unknown':
            cells = row.find_all(['td', 'th'])
            if len(cells) > 1:
                arch_name_tag = cells[1].find('a') or cells[1]
                arch_name = arch_name_tag.get_text(strip=True)
                tier_mapping[arch_name] = tier.replace('tier-', 'Tier ').title()
                
    return tier_mapping

def parse_matrix(html, time_frame, tier_mapping):
    if not html: return None
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', class_='winrates') or soup.find('table')
    if not table:
        print(f"No winrate table found for {time_frame}")
        return None
        
    rows = table.find_all('tr')
    if len(rows) < 2: return None
    
    headers = [c.get_text(strip=True) for c in rows[0].find_all(['td', 'th'])]
    opponents = headers[2:]
    
    matrix = {}
    archetypes = set()
    
    for row in rows[1:]:
        cells = row.find_all(['td', 'th'])
        if len(cells) < len(headers): continue
        
        archetype = cells[0].get_text(strip=True)
        if not archetype: continue
        
        archetypes.add(archetype)
        if archetype not in matrix:
            matrix[archetype] = {}
            
        for i, opp in enumerate(opponents):
            cell_idx = i + 2
            cell_html = str(cells[cell_idx])
            
            m = re.search(r'<b>(\d+)</b><span[^>]*>%</span>\s*<div[^>]*>([\d,]+)\s*matches</div>', cell_html)
            if m:
                win_pct = int(m.group(1)) / 100.0
                matches = int(m.group(2).replace(',', ''))
                wins = round(matches * win_pct)
                losses = matches - wins
                
                matrix[archetype][opp] = {
                    "archetype": opp,
                    "wins": wins,
                    "losses": losses,
                    "draws": 0,
                    "total_matches": matches,
                    "win_rate": win_pct
                }
                archetypes.add(opp)
                
    return {
        "time_frame": time_frame,
        "end_date": datetime.now().strftime("%Y-%m-%d"),
        "archetypes": sorted(list(archetypes)),
        "tiers": tier_mapping,
        "matrix": matrix
    }

def parse_meta_shares(html):
    if not html: return {}
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', class_='table-striped')
    if not table: return {}
    
    shares = {}
    for row in table.find_all('tr'):
        cols = row.find_all('td')
        if len(cols) < 3: continue
        name_tag = cols[1].find('strong')
        if not name_tag: continue
        name = name_tag.get_text(strip=True)
        share_text = cols[2].find('b')
        if share_text:
            try:
                val = float(share_text.get_text(strip=True).replace('%', '')) / 100.0
                shares[name] = val
            except: pass
    return shares

def merge_matrices(m1, m2):
    """Deep merge of two win rate matrices with weighted win rate."""
    if not m1: return m2
    if not m2: return m1
    
    merged_matrix = {}
    all_archs = set(list(m1.keys()) + list(m2.keys()))
    
    for arch in all_archs:
        merged_matrix[arch] = {}
        opps1 = m1.get(arch, {})
        opps2 = m2.get(arch, {})
        all_opps = set(list(opps1.keys()) + list(opps2.keys()))
        
        for opp in all_opps:
            s1 = opps1.get(opp, {"wins": 0, "losses": 0, "total_matches": 0})
            s2 = opps2.get(opp, {"wins": 0, "losses": 0, "total_matches": 0})
            
            total_wins = s1.get('wins', 0) + s2.get('wins', 0)
            total_matches = s1.get('total_matches', 0) + s2.get('total_matches', 0)
            
            if total_matches > 0:
                merged_matrix[arch][opp] = {
                    "archetype": opp,
                    "wins": total_wins,
                    "losses": total_matches - total_wins,
                    "draws": 0,
                    "total_matches": total_matches,
                    "win_rate": round(total_wins / total_matches, 4)
                }
            
    return merged_matrix

def total_matches_in_matrix(matrix):
    """Sum total_matches across the entire matrix (each game is counted twice: A vs B and B vs A)."""
    total = 0
    for arch, matchups in matrix.items():
        for opp, stats in matchups.items():
            total += stats.get('total_matches', 0)
    return total

def merge_meta_shares(shares_list, matrices_list):
    """
    Merge meta share dicts weighted by actual match count in the corresponding matrices.
    shares_list:   [s1, s2, ...]
    matrices_list: [m1, m2, ...] — must be same length
    """
    weights = [max(total_matches_in_matrix(m), 1) for m in matrices_list]
    total_weight = sum(weights)
    all_archs = set()
    for s in shares_list:
        all_archs.update(s.keys())
    merged = {}
    for arch in all_archs:
        merged[arch] = sum(s.get(arch, 0.0) * w for s, w in zip(shares_list, weights)) / total_weight
    return merged

import sys
import argparse

# --- Main Script ---

def main():
    parser = argparse.ArgumentParser(description='MTGDecks Monthly Data Update')
    parser.add_argument('--no-replace', action='store_true', help='Do not overwrite root data files, only create historical backup')
    args = parser.parse_args()

    # Identify current date and the previous month's backup folder
    current_date = datetime.now()
    # Normalize to 1st of the current month
    folder_name = current_date.strftime('%Y-%m-01')
    output_historical_dir = os.path.join(HISTORICAL_DIR, folder_name)
    os.makedirs(output_historical_dir, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    
    print(f"Starting monthly update for {folder_name}")
    if args.no_replace:
        print("!!! RUNNING IN NO-REPLACE MODE - Root data will NOT be updated !!!")
        
    print("---------------------------------------------------------------")
    print("Pripojuji se na tvuj Chrome! Zapni si ho s parametrem pro debug:")
    print("chrome.exe --remote-debugging-port=9222")
    print("Pote si rucne nacti mtgdecks.net, odklikej Cloudflare a pak tenhle skript najdi to bezi bez tve pomoci dal.")
    print("---------------------------------------------------------------")

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp('http://localhost:9222')
        except Exception as e:
            print("\n[CHYBA] Nepodarilo se pripojit k tvemu prohlizeci!")
            print("Zavri VSECHNA stavajici okna Chromu a pust do terminalu / prikazove radky tento prikaz:")
            print("  \"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe\" --remote-debugging-port=9222 --user-data-dir=\"C:\\Temp\\ChromeDebug\"")
            print("Jakmile se okno otevre, zadej mtgdecks.net preklikej CAPTCHU a spust tento skript znovu.\n")
            return
            
        context = browser.contexts[0]
        # Use the already open tab to ensure Cloudflare clearance holds
        if len(context.pages) > 0:
            page = context.pages[0]
        else:
            page = context.new_page()
    
        tiers = get_tiers(page)
        
        all_data = {} # store results for current run
    
        for label, wr_path, meta_path in SOURCES:
            data = None
            
            # 1. Fetch Metagame Shares
            meta_url = f"https://mtgdecks.net/Premodern/{meta_path}"
            meta_shares = parse_meta_shares(fetch_html(meta_url, page))
            
            # 2. Fetch Win Rates (if available)
            if wr_path:
                wr_url = f"https://mtgdecks.net/Premodern/winrates/{wr_path}"
                data = parse_matrix(fetch_html(wr_url, page), label, tiers)
            
            if not data:
                # Create stub for meta-only timeframes
                data = {
                    "time_frame": label,
                    "end_date": datetime.now().strftime("%Y-%m-%d"),
                    "archetypes": sorted(list(meta_shares.keys())),
                    "tiers": tiers,
                    "matrix": {}
                }
                
            data["meta_shares"] = meta_shares
            all_data[label] = data
            
            # Save to historical
            hist_path = os.path.join(output_historical_dir, f"mtgdecks_matrix_{label}.json")
            with open(hist_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
                
            # Optional save to root
            if not args.no_replace:
                root_path = os.path.join(DATA_DIR, f"mtgdecks_matrix_{label}.json")
                with open(root_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4)
                print(f"Saved {label} data to root and historical.")
            else:
                print(f"Saved {label} data to historical backup.")

    # --- SYNTHESIZING 90_DAYS DATA ---
    print("\nAttempting to synthesize 90_days data (prev 60_days + current 30_days)...")
    # Calculate the exact previous month folder name
    first_of_current = current_date.replace(day=1)
    prev_month_date = first_of_current - timedelta(days=1)
    prev_folder_name = prev_month_date.strftime('%Y-%m-01')
    prev_60_days_path = os.path.join(HISTORICAL_DIR, prev_folder_name, "mtgdecks_matrix_60_days.json")
    
    if "30_days" in all_data and os.path.exists(prev_60_days_path):
        try:
            with open(prev_60_days_path, 'r', encoding='utf-8') as f:
                prev_60_data = json.load(f)
                
            cur_30_data = all_data["30_days"]
            
            merged_matrix = merge_matrices(prev_60_data.get("matrix", {}), cur_30_data.get("matrix", {}))
            merged_meta = merge_meta_shares(
                [prev_60_data.get("meta_shares", {}), cur_30_data.get("meta_shares", {})],
                [prev_60_data.get("matrix", {}), cur_30_data.get("matrix", {})]
            )
            
            data_90 = {
                "time_frame": "90_days",
                "end_date": datetime.now().strftime("%Y-%m-%d"),
                "archetypes": sorted(list(set(prev_60_data.get("archetypes", []) + cur_30_data.get("archetypes", [])))),
                "tiers": tiers,
                "matrix": merged_matrix,
                "meta_shares": merged_meta
            }
            
            label_90 = "90_days"
            hist_path_90 = os.path.join(output_historical_dir, f"mtgdecks_matrix_{label_90}.json")
            with open(hist_path_90, 'w', encoding='utf-8') as f:
                json.dump(data_90, f, indent=4)
                
            if not args.no_replace:
                root_path_90 = os.path.join(DATA_DIR, f"mtgdecks_matrix_{label_90}.json")
                with open(root_path_90, 'w', encoding='utf-8') as f:
                    json.dump(data_90, f, indent=4)
                print(f"Successfully synthesized and saved 90_days data to root and historical using backup from {prev_folder_name}.")
            else:
                print(f"Successfully synthesized and saved 90_days data to historical backup using backup from {prev_folder_name}.")
                
        except Exception as e:
            print(f"Error synthesizing 90_days data: {e}")
    else:
        if "30_days" not in all_data:
            print("Failed to synthesize 90_days: 30_days data wasn't fetched today.")
        else:
            print(f"Failed to synthesize 90_days: Previous month backup not found at {prev_60_days_path}.")

    # --- SYNTHESIZING MAX TIMEFRAME (7 Months / 210 Days) ---
    print("\nAttempting to synthesize 210_days (7 month) data (prev 6 month + current 1 month)...")
    prev_180_days_path = os.path.join(HISTORICAL_DIR, prev_folder_name, "mtgdecks_matrix_180_days.json")
    
    if "30_days" in all_data and os.path.exists(prev_180_days_path):
        try:
            with open(prev_180_days_path, 'r', encoding='utf-8') as f:
                prev_180_data = json.load(f)
                
            cur_30_data = all_data["30_days"]
            
            merged_matrix = merge_matrices(prev_180_data.get("matrix", {}), cur_30_data.get("matrix", {}))
            
            # Combine meta shares weighted by actual match count in each period's matrix
            merged_meta = merge_meta_shares(
                [prev_180_data.get("meta_shares", {}), cur_30_data.get("meta_shares", {})],
                [prev_180_data.get("matrix", {}), cur_30_data.get("matrix", {})]
            )
            
            data_210 = {
                "time_frame": "210_days",
                "end_date": datetime.now().strftime("%Y-%m-%d"),
                "archetypes": sorted(list(set(prev_180_data.get("archetypes", []) + cur_30_data.get("archetypes", [])))),
                "tiers": tiers,
                "matrix": merged_matrix,
                "meta_shares": merged_meta
            }
            
            label_max = "210_days"
            hist_path_max = os.path.join(output_historical_dir, f"mtgdecks_matrix_{label_max}.json")
            with open(hist_path_max, 'w', encoding='utf-8') as f:
                json.dump(data_210, f, indent=4)
                
            if not args.no_replace:
                root_path_max = os.path.join(DATA_DIR, f"mtgdecks_matrix_{label_max}.json")
                with open(root_path_max, 'w', encoding='utf-8') as f:
                    json.dump(data_210, f, indent=4)
                print(f"Successfully synthesized and saved {label_max} data to root and historical using 6M backup from {prev_folder_name}.")
            else:
                print(f"Successfully synthesized and saved {label_max} data to historical backup using 6M backup from {prev_folder_name}.")
                
        except Exception as e:
            print(f"Error synthesizing {label_max} data: {e}")
    else:
        if "30_days" not in all_data:
            print("Failed to synthesize 210_days: 30_days data wasn't fetched today.")
        else:
            print(f"Failed to synthesize 210_days: Previous month 180_days backup not found at {prev_180_days_path}.")

    print("\nUpdate complete.")

if __name__ == "__main__":
    main()
