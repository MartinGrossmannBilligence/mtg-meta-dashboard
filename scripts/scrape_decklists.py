import urllib.request
import gzip
from bs4 import BeautifulSoup
import re
import json
import time
import math
import os
import shutil
from datetime import datetime

def backup_data_folder():
    if not os.path.exists('data'): return
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = f'data_backups/data_{timestamp}'
    try:
        shutil.copytree('data', backup_dir)
        print(f"Created backup of data/ at {backup_dir}")
    except Exception as e:
        print(f"Warning: Failed to create backup: {e}")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
MATRIX_FILE = os.path.join(DATA_DIR, "mtgdecks_matrix_6_months.json")
DECKLISTS_FILE = os.path.join(DATA_DIR, "decklists.json")

def get_html(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
        }
    )
    time.sleep(1.5)  # Be nice to the server
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            html_bytes = r.read()
            if r.info().get('Content-Encoding') == 'gzip':
                return gzip.decompress(html_bytes).decode('utf-8', errors='ignore')
            return html_bytes.decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def fetch_cards(deck_url):
    html = get_html(deck_url)
    if not html: return []
    
    soup = BeautifulSoup(html, 'html.parser')
    cards = []
    
    current_section = "Maindeck"
    current_type = "Other"
    
    # MTGDecks often uses <th> for types/sections
    rows = soup.find_all('tr')
    for row in rows:
        # Check for header rows that define sections/types
        th = row.find('th')
        if th:
            txt = th.get_text(strip=True).lower()
            if 'sideboard' in txt:
                current_section = "Sideboard"
                current_type = "Other"
            elif '[' in txt and '(' not in txt: # Likely a type like "Creatures [15]"
                current_type = txt.split('[')[0].strip().capitalize()
            continue
            
        td_num = row.find('td', class_='number')
        if not td_num: continue
        
        # Quantity is usually the text DIRECTLY inside td.number, 
        # but sometimes there's an <a> or <span> first.
        # Cleanly extract just the digits.
        qty_text = "".join(filter(str.isdigit, td_num.get_text(separator=' ', strip=True)))
        if not qty_text: continue
        qty = int(qty_text)
        
        name_tag = row.find('a')
        if name_tag:
            name = name_tag.get_text(strip=True)
            cards.append({
                "qty": qty, 
                "name": name,
                "section": current_section,
                "type": current_type
            })
            
    return cards[:100]

def scrape_archetype_decklists(archetype_name, max_pages=10, required_decks=10):
    slug = archetype_name.replace(" ", "-").replace("(", "").replace(")", "").replace("'", "")
    
    # Custom slug overrides for MTGDecks
    if archetype_name == "RG Oath": slug = "rg-oath"
    if archetype_name == "Suicide Black": slug = "suicide-black"
    if archetype_name == "UW Standstill": slug = "uw-standstill"
    if archetype_name == "Lands": slug = "lands"
    if archetype_name == "Pyrostatic Oath": slug = "pyrostatic-oath"
    if archetype_name == "Sneak Attack": slug = "sneak-and-show"
    if archetype_name == "Temping Rack": slug = "tempting-rack"
    if archetype_name == "UR Control": slug = "u-r-control"
    
    print(f"\nScraping {archetype_name} (slug: {slug})...")
    
    # Define rank priorities for scoring
    rank_scores = {
        '1st': 100, '1': 100,
        '2nd': 85,  '2': 85,
        '3rd': 70,  '3': 70,
        '4th': 70,  '4': 70,
        'top4': 70,
        '5th': 55,  '5': 55,
        '6th': 55,  '6': 55,
        '7th': 55,  '7': 55,
        '8th': 55,  '8': 55,
        'top8': 55,
        'top16': 30,
        'top32': 15,
        'top64': 5
    }
    
    collected_candidates = []
    
    for page in range(1, max_pages + 1):
        url = f"https://mtgdecks.net/Premodern/{slug}"
        if page > 1:
            url += f"/page:{page}"
            
        print(f"  Fetching page {page} -> {url}")
        html = get_html(url)
        if not html:
            break
            
        soup = BeautifulSoup(html, 'html.parser')
        rows = soup.find_all('tr')
        if not rows or len(rows) < 5:
            break
            
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 6:
                continue
                
            try:
                rank_text = cols[0].get_text(strip=True).split('(')[0].strip()
                player_td = cols[2]
                deck_link = player_td.find('a')
                if not deck_link: continue
                deck_url = deck_link['href']
                if deck_url.startswith('/'):
                    deck_url = 'https://mtgdecks.net' + deck_url
                
                strong_tag = player_td.find('strong')
                player = strong_tag.get_text(strip=True).replace('By', '').strip() if strong_tag else "Unknown"
                event = cols[5].get_text(strip=True)
                
                players_text = cols[7].get_text(strip=True)
                players = int(re.sub(r'\D', '', players_text)) if players_text and re.sub(r'\D', '', players_text) else 0
                date_text = cols[9].get_text(separator=' ', strip=True)
                
                # Colors
                color_td = cols[3]
                colors_list = []
                for span in color_td.find_all('span', class_='ms-cost'):
                    for cls in span.get('class', []):
                        if cls.startswith('ms-') and len(cls) == 4 and cls != 'ms-cost':
                            colors_list.append(cls.replace('ms-', '').upper())
                            
                # Spiciness
                spice_td = cols[8]
                spice_bar = spice_td.find('div', class_='progress-bar')
                spice_val = int(spice_bar['aria-valuenow']) if spice_bar and 'aria-valuenow' in spice_bar.attrs else 0
                
                rank_lower = rank_text.lower()
                
                # TPS SCORING MODEL
                # 1. Base points from rank
                rank_points = rank_scores.get(rank_lower, 0)
                if not rank_points:
                    match_rank = re.search(r'(\d+)', rank_lower)
                    if match_rank:
                        val = int(match_rank.group(1))
                        if val == 1: rank_points = 100
                        elif val == 2: rank_points = 85
                        elif val <= 4: rank_points = 70
                        elif val <= 8: rank_points = 55
                        elif val <= 16: rank_points = 30
                        elif val <= 32: rank_points = 15
                
                if rank_points == 0: continue
                
                # 2. Logarithmic Multiplier (Log2(Players) / 5)
                # 32 players -> 5.0/5.0 = 1.0x
                # 64 players -> 6.0/5.0 = 1.2x
                # 128 players -> 7.0/5.0 = 1.4x
                # Ensure players is at least 8 to avoid negative/too low multipliers
                effective_players = max(players, 8)
                multiplier = math.log2(effective_players) / 5.0
                tps_score = rank_points * multiplier
                
                collected_candidates.append({
                    "player": player,
                    "rank": rank_text,
                    "players": players,
                    "event": event,
                    "date": date_text,
                    "url": deck_url,
                    "colors": list(set(colors_list)),
                    "spice": spice_val,
                    "tps_score": tps_score
                })
            except Exception as e:
                pass
                
    # Sort collected candidates by TPS score descending, then players descending
    collected_candidates.sort(key=lambda x: (x["tps_score"], x["players"]), reverse=True)
    
    # Remove duplicates by URL
    seen_urls = set()
    unique_candidates = []
    for d in collected_candidates:
        if d['url'] not in seen_urls:
            unique_candidates.append(d)
            seen_urls.add(d['url'])
    
    # Take the top N required
    final_selection = unique_candidates[:required_decks]
    
    # Now fetch the cards only for the selected top decks
    final_decks = []
    for count, deck in enumerate(final_selection):
        print(f"    [{count+1}/{len(final_selection)}] Fetching cards for {deck['rank']} by {deck['player']} (Players: {deck['players']}, Score: {deck['tps_score']:.2f})")
        cards = fetch_cards(deck['url'])
        
        final_decks.append({
            "player": deck["player"],
            "rank": deck["rank"],
            "players": deck["players"],
            "event": deck["event"],
            "date": deck["date"],
            "url": deck["url"],
            "colors": deck["colors"],
            "spice": deck["spice"],
            "cards": cards
        })
        
    return final_decks

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Scrape decklists from MTGDecks')
    parser.add_argument('--force', action='store_true', help='Force re-scraping even if decklists exist')
    args = parser.parse_args()
    
    backup_data_folder()
    
    # Use 60 days as primary source, fallback to 6 months
    matrix_path = os.path.join(DATA_DIR, "mtgdecks_matrix_60_days.json")
    if not os.path.exists(matrix_path):
        matrix_path = MATRIX_FILE
        
    if not os.path.exists(matrix_path):
        print(f"Matrix file not found: {matrix_path}")
        return
        
    print(f"Loading archetypes from: {matrix_path}")
    with open(matrix_path, 'r', encoding='utf-8') as f:
        matrix_data = json.load(f)
        
    archetypes = matrix_data.get('archetypes', [])
    print(f"Found {len(archetypes)} total archetypes to process.")
    
    # We will load existing decklists so we can resume/update without destroying everything
    decklists_db = {}
    if os.path.exists(DECKLISTS_FILE):
        with open(DECKLISTS_FILE, 'r', encoding='utf-8') as f:
            try:
                decklists_db = json.load(f)
            except:
                pass
                
    for arch in archetypes:
        # RESUME LOGIC: Skip if we already have 10 decklists AND they have card data (unless --force)
        if not args.force:
            existing_decks = decklists_db.get(arch, [])
            has_cards = any(d.get('cards') for d in existing_decks)
            
            if len(existing_decks) >= 10 and has_cards:
                print(f"Skipping {arch} - already have {len(existing_decks)} decklists with card data.")
                continue

        try:
            # Fresh scan of 10 pages to find the best 10 decks
            decks = scrape_archetype_decklists(arch, max_pages=10, required_decks=10)
            if decks:
                decklists_db[arch] = decks
                
                # Save progressively
                with open(DECKLISTS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(decklists_db, f, indent=2)
            
        except Exception as e:
            print(f"Critical error on {arch}: {e}")
            
    print("\nScraping complete! Data saved to data/decklists.json.")

if __name__ == "__main__":
    main()
