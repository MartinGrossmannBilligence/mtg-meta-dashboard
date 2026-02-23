import urllib.request
import urllib.error
from bs4 import BeautifulSoup
import re
import streamlit as st

@st.cache_data(ttl=86400, show_spinner="Fetching latest decks from mtgdecks.net...")
def get_recent_top_decks(archetype_name):
    """
    Scrape mtgdecks.net for the given archetype and return up to 10 recent decklists
    from tournaments with >= 100 players where the deck made Top 8.
    """
    
    # Map typical names to mtgdecks slugs
    # e.g., "Blue/Black Psychatog" -> "psychatog"
    slug = archetype_name.lower().replace('/', '-').replace(' ', '-')
    
    # Custom mapping for known drift
    mapping = {
        "blue-black-psychatog": "psychatog",
        "the-rock": "the-rock",
        "uw-standstill": "uw-standstill",
        "survival-welder": "survival-welder",
        "stiflenought": "stiflenought",
        "goblins": "goblins",
        "sligh": "sligh",
        "deadguy-ale": "deadguy-ale",
        "burn": "burn",
        "elfball": "elves",
        "landstill": "uw-standstill",  # fallback or guess
    }
    
    slug = mapping.get(slug, slug)
    
    url = f"https://mtgdecks.net/Premodern/{slug}"
    
    try:
        req = urllib.request.Request(
            url, 
            data=None, 
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return []

    soup = BeautifulSoup(html, 'html.parser')
    
    table = soup.find('table', class_='clickable')
    if not table:
        return []
    
    top_decks = []
    
    valid_ranks = ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "top 4", "top 8", "1", "2", "3", "4", "5", "6", "7", "8", "top4", "top8"]
    
    for row in table.find_all('tr'):
        cols = row.find_all('td')
        if len(cols) < 6:
            continue
        
        try:
            # 0: Rank, 1: blank, 2: Player/DeckName, 3: Colors, 4: Format, 5: Event, 6: Level, 7: Players, 8: Spiciness, 9: Date
            rank_text = cols[0].get_text(strip=True).split('(')[0].strip()
            
            player_td = cols[2]
            deck_link = player_td.find('a')
            deck_url = deck_link['href'] if deck_link else ""
            
            strong_tag = player_td.find('strong')
            player = strong_tag.get_text(strip=True).replace('By', '').strip() if strong_tag else "Unknown"
            
            event = cols[5].get_text(strip=True)
            
            players_text = cols[7].get_text(strip=True)
            players = int(re.sub(r'\D', '', players_text)) if players_text and re.sub(r'\D', '', players_text) else 0
            
            date_text = cols[9].get_text(separator=' ', strip=True) # e.g. "21-Feb -2026"
            
            if not deck_url:
                continue
                
            rank_lower = rank_text.lower()
            is_top_8 = any(r == rank_lower or rank_lower.startswith(r) for r in valid_ranks)
            
            if players >= 100 and is_top_8:
                top_decks.append({
                    "player": player,
                    "rank": rank_text,
                    "players": players,
                    "event": event,
                    "date": date_text,
                    "url": "https://mtgdecks.net" + deck_url if not deck_url.startswith('http') else deck_url
                })
                
            if len(top_decks) >= 10:
                break
                
        except Exception as e:
            print(f"Error parsing row: {e}")
            continue
            
    return top_decks
