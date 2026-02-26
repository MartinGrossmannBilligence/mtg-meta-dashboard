import urllib.request
import urllib.error
import gzip
import json
import re
import os
from bs4 import BeautifulSoup
from datetime import datetime
import shutil

def backup_data_folder():
    if not os.path.exists('data'): return
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = f'data_backups/data_{timestamp}'
    try:
        shutil.copytree('data', backup_dir)
        print(f"Created backup of data/ at {backup_dir}")
    except Exception as e:
        print(f"Warning: Failed to create backup: {e}")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

def fetch_html(url):
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
        # Classes like 'tier-1', 'tier-2', 'tier-3'
        tier = next((c for c in classes if c.startswith('tier-') and c != 'tier-all'), 'tier-unknown')
        if tier != 'tier-unknown':
            cells = row.find_all(['td', 'th'])
            if len(cells) > 1:
                arch_name_tag = cells[1].find('a') or cells[1]
                arch_name = arch_name_tag.get_text(strip=True)
                tier_mapping[arch_name] = tier.replace('tier-', 'Tier ').title()
                
    return tier_mapping

def fetch_matrix(url, time_frame, tier_mapping):
    print(f"Fetching matrix for {time_frame} from {url}...")
    html = fetch_html(url)
    if not html: return None
    
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', class_='winrates') or soup.find('table')
    if not table:
        print(f"No winrate table found for {time_frame}")
        return None
        
    rows = table.find_all('tr')
    if len(rows) < 2: return None
    
    headers = [c.get_text(strip=True) for c in rows[0].find_all(['td', 'th'])]
    # Headers[0] is blank, Headers[1] is Overall, rest are archetypes
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
            
            # Extract winrate and matches
            # e.g., <b>51</b><span class="percent">%</span> ... <div class="matches-number">83 matches</div>
            import re
            m = re.search(r'<b>(\d+)</b><span[^>]*>%</span>\s*<div[^>]*>([\d,]+)\s*matches</div>', cell_html)
            if m:
                win_pct = int(m.group(1)) / 100.0
                matches = int(m.group(2).replace(',', ''))
                
                # Approximate wins and losses
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
        "start_date": "",
        "end_date": datetime.now().strftime("%Y-%m-%d"),
        "min_percentage": 0,
        "archetypes": sorted(list(archetypes)),
        "tiers": tier_mapping, # Save tiers alongside the matrix
        "matrix": matrix
    }

def fetch_meta_shares(url):
    print(f"Fetching meta shares from {url}...")
    html = fetch_html(url)
    if not html: return {}
    
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', class_='table-striped')
    if not table: return {}
    
    shares = {}
    for row in table.find_all('tr'):
        cols = row.find_all('td')
        if len(cols) < 3: continue
        
        # Archetype name in 2nd column
        name_tag = cols[1].find('strong')
        if not name_tag: continue
        name = name_tag.get_text(strip=True)
        
        # Share percentage in 3rd column
        share_text = cols[2].find('b')
        if share_text:
            try:
                # Convert "7.96%" to 0.0796
                val = float(share_text.get_text(strip=True).replace('%', '')) / 100.0
                shares[name] = val
            except:
                pass
                
    return shares

def main():
    backup_data_folder()
    
    tiers = get_tiers()
    print(f"Loaded {len(tiers)} archetype tiers.")
    
    # We map timeframe names to (Winrate URL, Metagame URL)
    sources = {
        "2 Months": (
            "https://mtgdecks.net/Premodern/winrates/range:last60days",
            "https://mtgdecks.net/Premodern/metagame:last-2-months"
        ),
        "6 Months": (
            "https://mtgdecks.net/Premodern/winrates/range:last180days",
            "https://mtgdecks.net/Premodern/metagame:last-6-months"
        ),
        "1 Year": (
            "https://mtgdecks.net/Premodern/winrates/range:last365days",
            "https://mtgdecks.net/Premodern/metagame:last-year"
        ),
        "all_time": (
            "https://mtgdecks.net/Premodern/winrates",
            "https://mtgdecks.net/Premodern/metagame:last-2-years"
        ),
        "1 Month": (
            "https://mtgdecks.net/Premodern/winrates/range:last30days",
            "https://mtgdecks.net/Premodern/metagame:last-month"
        )
    }
    
    os.makedirs('data', exist_ok=True)
    
    for timeframe, (wr_url, meta_url) in sources.items():
        data = fetch_matrix(wr_url, timeframe, tiers)
        if data:
            # Add meta shares
            shares = fetch_meta_shares(meta_url)
            data["meta_shares"] = shares
            
            filename = timeframe.lower().replace(' ', '_')
            filepath = f"data/mtgdecks_matrix_{filename}.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            print(f"Saved {filepath} with {len(shares)} meta share entries.")

if __name__ == "__main__":
    main()
