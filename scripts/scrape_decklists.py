import urllib.request
import gzip
from bs4 import BeautifulSoup
import re
import json
import time
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
    for td in soup.find_all('td', class_='number'):
        row = td.find_parent('tr')
        if not row: continue
        
        qty_text = td.get_text(strip=True)
        if not qty_text.isdigit(): continue
            
        qty = int(qty_text)
        name_tag = row.find('a')
        if name_tag:
            name = name_tag.get_text(strip=True)
            cards.append({"qty": qty, "name": name})
            
    return cards[:75]

def scrape_archetype_decklists(archetype_name, max_pages=10, required_decks=10):
    slug = archetype_name.replace(" ", "-").replace("(", "").replace(")", "").replace("'", "")
    
    # Custom slug overrides for MTGDecks
    if archetype_name == "RG Oath": slug = "rg-oath"
    if archetype_name == "Suicide Black": slug = "suicide-black"
    if archetype_name == "UW Standstill": slug = "uw-standstill"
    
    print(f"\nScraping {archetype_name} (slug: {slug})...")
    
    # Define rank priorities for scoring
    rank_scores = {
        '1st': 100, '1': 100,
        '2nd': 90,  '2': 90,
        '3rd': 80,  '3': 80,
        '4th': 80,  '4': 80,
        'top4': 80,
        '5th': 70,  '5': 70,
        '6th': 70,  '6': 70,
        '7th': 70,  '7': 70,
        '8th': 70,  '8': 70,
        'top8': 70,
        'top16': 50,
        'top32': 30,
        'top64': 20,
        'top128': 10
    }
    
    collected_candidates = []
    
    for page in range(1, max_pages + 1):
        # We search all max_pages to get the best possible selection
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
                
                # Check eligibility
                is_top_8 = any(r in rank_lower for r in ['1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', 'top4', 'top8', ' 1 ', ' 2 ', ' 3 ', ' 4 ', ' 5 ', ' 6 ', ' 7 ', ' 8 '])
                if rank_lower in ['1','2','3','4','5','6','7','8']: is_top_8 = True
                
                is_top_4 = any(r in rank_lower for r in ['1st', '2nd', '3rd', '4th', 'top4', ' 1 ', ' 2 ', ' 3 ', ' 4 '])
                if rank_lower in ['1','2','3','4']: is_top_4 = True

                # PRIMARY CRITERIA: Top 8 / 65+ players OR Top 4 / 33+ players
                meets_primary = (is_top_8 and players >= 65) or (is_top_4 and players >= 33)
                
                # Fallback ranking score
                score = rank_scores.get(rank_lower, 0)
                # If rank contains a number, try to extract it
                if not score:
                    match_rank = re.search(r'(\d+)', rank_lower)
                    if match_rank:
                        val = int(match_rank.group(1))
                        if val == 1: score = 100
                        elif val == 2: score = 90
                        elif val <= 4: score = 80
                        elif val <= 8: score = 70
                        elif val <= 16: score = 50
                        elif val <= 32: score = 30
                
                collected_candidates.append({
                    "player": player,
                    "rank": rank_text,
                    "players": players,
                    "event": event,
                    "date": date_text,
                    "url": deck_url,
                    "colors": list(set(colors_list)),
                    "spice": spice_val,
                    "meets_primary": meets_primary,
                    "score": score
                })
            except Exception as e:
                pass
                
    # Sort collected candidates:
    # 1. Meets primary criteria first
    # 2. Score descending (Rank weight)
    # 3. Number of players descending (Tie-breaker)
    collected_candidates.sort(key=lambda x: (x["meets_primary"], x["score"], x["players"]), reverse=True)
    
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
        print(f"    [{count+1}/{len(final_selection)}] Fetching cards for {deck['rank']} by {deck['player']} (Players: {deck['players']}, Primary: {deck['meets_primary']})")
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
    backup_data_folder()
    
    if not os.path.exists(MATRIX_FILE):
        print(f"Matrix file not found: {MATRIX_FILE}")
        return
        
    with open(MATRIX_FILE, 'r', encoding='utf-8') as f:
        matrix_data = json.load(f)
        
    archetypes = matrix_data.get('archetypes', [])
    tiers = matrix_data.get('tiers', {})
    
    # Filter to only Tier 1 and Tier 2 archetypes
    tier_archetypes = [arch for arch in archetypes if tiers.get(arch) in ["Tier 1", "Tier 2"]]
    print(f"Found {len(tier_archetypes)} Tier 1 & 2 archetypes to scrape out of {len(archetypes)} total.")
    
    # We will load existing decklists so we can resume/update without destroying everything
    decklists_db = {}
    if os.path.exists(DECKLISTS_FILE):
        with open(DECKLISTS_FILE, 'r', encoding='utf-8') as f:
            try:
                decklists_db = json.load(f)
            except:
                pass
                
    for arch in tier_archetypes:
        # User requested fresh scan of 10 pages for all Tier 1/2 archetypes
        try:
            decks = scrape_archetype_decklists(arch, max_pages=10, required_decks=10)
            decklists_db[arch] = decks
            
            # Save progressively in case it crashes
            with open(DECKLISTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(decklists_db, f, indent=2)
                
        except Exception as e:
            print(f"Critical error on {arch}: {e}")
            
    print("\nScraping complete! Data saved to data/decklists.json.")

if __name__ == "__main__":
    main()
