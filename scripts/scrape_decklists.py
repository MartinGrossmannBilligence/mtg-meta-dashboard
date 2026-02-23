import urllib.request
import gzip
from bs4 import BeautifulSoup
import re
import json
import time
import os

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

def scrape_archetype_decklists(archetype_name, max_pages=3, required_decks=5):
    slug = archetype_name.replace(" ", "-").replace("(", "").replace(")", "").replace("'", "")
    
    # Custom slug overrides for MTGDecks
    if archetype_name == "RG Oath": slug = "rg-oath"
    if archetype_name == "Suicide Black": slug = "suicide-black"
    if archetype_name == "UW Standstill": slug = "uw-standstill"
    # Basic slug parsing works for most
    
    print(f"\nScraping {archetype_name} (slug: {slug})...")
    
    valid_ranks =['1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', 'top4', 'top8', '1', '2', '3', '4', '5', '6', '7', '8']
    top_decks = []
    
    for page in range(1, max_pages + 1):
        if len(top_decks) >= required_decks:
            break
            
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
            # Reached the end of pagination
            break
            
        for row in rows:
            if len(top_decks) >= required_decks:
                break
                
            cols = row.find_all('td')
            if len(cols) < 6:
                continue
                
            try:
                rank_text = cols[0].get_text(strip=True).split('(')[0].strip()
                player_td = cols[2]
                deck_link = player_td.find('a')
                if not deck_link: continue
                deck_url = deck_link['href']
                
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
                is_top_8 = any(r == rank_lower or rank_lower.startswith(r) for r in valid_ranks)
                
                if players == 0:
                    match_record = re.match(r'^(\d+)-(\d+)(?:-(\d+))?$', rank_text)
                    if match_record:
                        wins, losses = int(match_record.group(1)), int(match_record.group(2))
                        draws = int(match_record.group(3)) if match_record.group(3) else 0
                        total_rounds = wins + losses + draws
                        if total_rounds >= 8: players = 129
                        elif total_rounds == 7: players = 65
                        elif total_rounds == 6: players = 33
                        elif total_rounds == 5: players = 17
                        if wins >= 3 and losses == 0:
                            is_top_8 = True
                            
                if players >= 50 and is_top_8:
                    print(f"    [+] Found valid deck: {rank_text} by {player} ({players} players)")
                    cards = fetch_cards(deck_url)
                    top_decks.append({
                        "player": player,
                        "rank": rank_text,
                        "players": players,
                        "event": event,
                        "date": date_text,
                        "url": deck_url,
                        "colors": list(set(colors_list)),
                        "spice": spice_val,
                        "cards": cards
                    })
            except Exception as e:
                pass
                
    return top_decks

def main():
    if not os.path.exists(MATRIX_FILE):
        print(f"Matrix file not found: {MATRIX_FILE}")
        return
        
    with open(MATRIX_FILE, 'r', encoding='utf-8') as f:
        matrix_data = json.load(f)
        
    archetypes = matrix_data.get('archetypes', [])
    print(f"Found {len(archetypes)} archetypes to scrape.")
    
    # We will load existing decklists so we can resume/update without destroying everything
    decklists_db = {}
    if os.path.exists(DECKLISTS_FILE):
        with open(DECKLISTS_FILE, 'r', encoding='utf-8') as f:
            try:
                decklists_db = json.load(f)
            except:
                pass
                
    for arch in archetypes:
        try:
            decks = scrape_archetype_decklists(arch)
            decklists_db[arch] = decks
            
            # Save progressively in case it crashes
            with open(DECKLISTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(decklists_db, f, indent=2)
                
        except Exception as e:
            print(f"Critical error on {arch}: {e}")
            
    print("\nScraping complete! Data saved to data/decklists.json.")

if __name__ == "__main__":
    main()
