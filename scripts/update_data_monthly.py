import urllib.request
import urllib.error
import gzip
import json
import re
import os
import shutil
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# --- Configuration ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
HISTORICAL_DIR = os.path.join(DATA_DIR, 'historical')

# Sources definition
# (Timeframe Label, Winrate Path, Metagame Path)
# None for Winrate Path means skip WR for that timeframe
SOURCES = [
    ("30_days", "range:last30days", "metagame:last-month"),
    ("60_days", "range:last60days", "metagame:last-2-months"),
    ("180_days", "range:last180days", "metagame:last-6-months"),
    ("1_year", None, "metagame:last-year"),
    ("2_years", None, "metagame:last-2-years")
]

# --- Helper Functions ---

def fetch_html(url):
    print(f"Fetching: {url}")
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            html_bytes = response.read()
            if response.info().get('Content-Encoding') == 'gzip':
                html_bytes = gzip.decompress(html_bytes)
            return html_bytes.decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def get_tiers():
    print("Fetching tiers from MTGDecks...")
    html = fetch_html('https://mtgdecks.net/Premodern')
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

def average_meta_shares(s1, s2):
    """Average meta shares. Ideally would be weighted by matches, but matches aren't available for meta shares easily."""
    if not s1: return s2
    if not s2: return s1
    all_archs = set(list(s1.keys()) + list(s2.keys()))
    merged_shares = {}
    for arch in all_archs:
        v1 = s1.get(arch, 0.0)
        v2 = s2.get(arch, 0.0)
        merged_shares[arch] = (v1 + v2) / 2.0
    return merged_shares

import sys
import argparse

# --- Main Script ---

def main():
    parser = argparse.ArgumentParser(description='MTGDecks Monthly Data Update')
    parser.add_argument('--no-replace', action='store_true', help='Do not overwrite root data files, only create historical backup')
    args = parser.parse_args()

    current_date = datetime.now()
    # Normalize to 1st of the current month
    folder_name = current_date.strftime('%Y-%m-01')
    output_historical_dir = os.path.join(HISTORICAL_DIR, folder_name)
    os.makedirs(output_historical_dir, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    
    print(f"Starting monthly update for {folder_name}")
    if args.no_replace:
        print("!!! RUNNING IN NO-REPLACE MODE - Root data will NOT be updated !!!")
    
    tiers = get_tiers()
    
    all_data = {} # store results for current run
    
    for label, wr_path, meta_path in SOURCES:
        data = None
        
        # 1. Fetch Metagame Shares
        meta_url = f"https://mtgdecks.net/Premodern/{meta_path}"
        meta_shares = parse_meta_shares(fetch_html(meta_url))
        
        # 2. Fetch Win Rates (if available)
        if wr_path:
            wr_url = f"https://mtgdecks.net/Premodern/winrates/{wr_path}"
            data = parse_matrix(fetch_html(wr_url), label, tiers)
        
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

    print("Update complete.")

if __name__ == "__main__":
    main()
