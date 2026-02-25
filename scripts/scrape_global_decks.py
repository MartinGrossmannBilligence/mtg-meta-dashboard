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

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DECKLISTS_FILE = os.path.join(DATA_DIR, "decklists.json")

# Ensure data dir exists
os.makedirs(DATA_DIR, exist_ok=True)

def get_html(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
        }
    )
    time.sleep(1.0)  # Rate limiting
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            html_bytes = r.read()
            if r.info().get('Content-Encoding') == 'gzip':
                return gzip.decompress(html_bytes).decode('utf-8', errors='ignore')
            return html_bytes.decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def fetch_cards(deck_url):
    print(f"    Fetching cards from {deck_url}...")
    html = get_html(deck_url)
    if not html: return []
    
    soup = BeautifulSoup(html, 'html.parser')
    cards = []
    # Similar to existing logic in scrape_decklists.py
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
            
    return cards[:75]  # Limit to 75 to avoid bloat (Main + Side)

def parse_rank(rank_str):
    rank_str = rank_str.lower().strip()
    if '1st' in rank_str or rank_str == '1': return 1
    if '2nd' in rank_str or rank_str == '2': return 2
    if '3rd' in rank_str or '4th' in rank_str or 'top4' in rank_str or rank_str in ['3', '4']: return 4
    if 'top8' in rank_str or any(x in rank_str for x in ['5th', '6th', '7th', '8th']) or rank_str in ['5', '6', '7', '8']: return 8
    
    # Try to extract number if it's "Top 16", "Top 32"
    match = re.search(r'top\s*(\d+)', rank_str)
    if match: return int(match.group(1))
    
    return 999  # Other / Unknown

def scrape_pages(num_pages=10):
    all_decks = []
    seen_urls = set()
    
    for page in range(1, num_pages + 1):
        url = "https://mtgdecks.net/Premodern"
        if page > 1:
            url += f"/page:{page}"
            
        print(f"Scraping page {page}: {url}")
        html = get_html(url)
        if not html:
            print("  Failed to fetch page, stopping.")
            break
            
        soup = BeautifulSoup(html, 'html.parser')
        container = soup.find('table', class_='table-striped')
        if not container:
            # Try alternate find
            rows = soup.find_all('tr')
        else:
            rows = container.find_all('tr')
            
        if not rows:
            print("  No rows found.")
            break
            
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 6: continue
            
            try:
                # 0: Rank, 1: Archetype, 2: Player, 3: Colors, 5: Event, 7: Players, 8: Spice, 9: Date
                rank_raw = cols[0].get_text(strip=True).split('(')[0].strip()
                rank_val = parse_rank(rank_raw)
                
                archetype = cols[1].get_text(strip=True)
                
                player_td = cols[2]
                deck_link = player_td.find('a')
                if not deck_link: continue
                deck_url = deck_link['href']
                if deck_url.startswith('/'):
                    deck_url = 'https://mtgdecks.net' + deck_url
                
                if deck_url in seen_urls: continue
                seen_urls.add(deck_url)
                
                strong_tag = player_td.find('strong')
                player = strong_tag.get_text(strip=True).replace('By', '').strip() if strong_tag else "Unknown"
                
                event = cols[5].get_text(strip=True)
                
                players_text = cols[7].get_text(strip=True)
                players_count = int(re.sub(r'\D', '', players_text)) if players_text and re.sub(r'\D', '', players_text) else 0
                
                # Colors
                color_td = cols[3]
                colors_list = []
                for span in color_td.find_all('span', class_='ms-cost'):
                    for cls in span.get('class', []):
                        if cls.startswith('ms-') and len(cls) == 4 and cls != 'ms-cost':
                            colors_list.append(cls.replace('ms-', '').upper())
                
                # Spice
                spice_td = cols[8]
                spice_bar = spice_td.find('div', class_='progress-bar')
                spice_val = int(spice_bar['aria-valuenow']) if spice_bar and 'aria-valuenow' in spice_bar.attrs else 0
                
                date_text = cols[9].get_text(separator=' ', strip=True)
                
                all_decks.append({
                    "archetype": archetype,
                    "player": player,
                    "rank": rank_raw,
                    "rank_val": rank_val,
                    "players": players_count,
                    "event": event,
                    "date": date_text,
                    "url": deck_url,
                    "colors": list(set(colors_list)),
                    "spice": spice_val
                })
            except Exception as e:
                # print(f"  Error parsing row: {e}")
                pass
                
    return all_decks

def filter_and_update(decks):
    # Load existing
    db = {}
    if os.path.exists(DECKLISTS_FILE):
        with open(DECKLISTS_FILE, 'r', encoding='utf-8') as f:
            try: db = json.load(f)
            except: pass
            
    # Track existing URLs to avoid duplicates
    existing_urls = set()
    for arch in db:
        for d in db[arch]:
            if 'url' in d: existing_urls.add(d['url'])
            
    # Count how many new high-quality decks we find
    new_count = 0
    
    # Priority conditions
    # 1. (Rank <= 8 & Players >= 65)
    # 2. (Rank <= 4 & Players >= 33)
    
    filtered_new = []
    for d in decks:
        if d['url'] in existing_urls: continue
        
        passes = False
        if d['rank_val'] <= 8 and d['players'] >= 65: passes = True
        elif d['rank_val'] <= 4 and d['players'] >= 33: passes = True
        
        if passes:
            filtered_new.append(d)
            
    # Fallback: if we didn't find many, take others sorted by rank/players
    # But for now, let's just use the filtered ones and see what we get.
    # The user said: "if not enough find, supplement with higher ranked"
    
    # Let's sort all scraped decks to find "backups"
    decks.sort(key=lambda x: (x['rank_val'], -x['players']))
    
    # We'll try to find at least 50 high quality decks total?
    # Actually, let's just take the top 50-100 from the whole scrape.
    
    final_decks_to_fetch = filtered_new[:100] # Cap fetching to be reasonable
    
    if len(final_decks_to_fetch) < 20:
        # Supplement with others
        for d in decks:
            if d['url'] in existing_urls: continue
            if d in final_decks_to_fetch: continue
            final_decks_to_fetch.append(d)
            if len(final_decks_to_fetch) >= 40: break

    print(f"Total new decks to integrate: {len(final_decks_to_fetch)}")
    
    for d in final_decks_to_fetch:
        arch = d['archetype']
        if arch not in db: db[arch] = []
        
        # Check if already in list (some might have been added in this loop)
        if any(x['url'] == d['url'] for x in db[arch]): continue
        
        # Fetch cards
        cards = fetch_cards(d['url'])
        
        entry = {
            "player": d["player"],
            "rank": d["rank"],
            "players": d["players"],
            "event": d["event"],
            "date": d["date"],
            "url": d["url"],
            "colors": d["colors"],
            "spice": d["spice"],
            "cards": cards
        }
        
        db[arch].insert(0, entry) # Add to start (most recent)
        new_count += 1
        
        # Keep only top 15 per archetype to save space
        db[arch] = db[arch][:15]
        
    # Save back
    with open(DECKLISTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=2)
        
    print(f"Integration complete. Added {new_count} new decks.")

if __name__ == "__main__":
    backup_data_folder()
    print("Starting global Premodern decklist scrape...")
    scraped_decks = scrape_pages(10)
    print(f"Scraped {len(scraped_decks)} candidate decks from 10 pages.")
    filter_and_update(scraped_decks)
    print("Done.")
