import urllib.request
import gzip
import json
import time
import re
import io

class MoxfieldAPI:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
        }

    def _get_html(self, url):
        req = urllib.request.Request(url, headers=self.headers)
        time.sleep(1.0)
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                html_bytes = r.read()
                if r.info().get('Content-Encoding') == 'gzip':
                    return gzip.decompress(html_bytes).decode('utf-8', errors='ignore')
                return html_bytes.decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    def extract_deck_id(self, url):
        """Extracts the deck ID from a Moxfield URL."""
        match = re.search(r'moxfield\.com/decks/([^/?#]+)', url)
        if match:
            return match.group(1)
        return None

    def fetch_deck(self, deck_id_or_url):
        """Fetches deck data from Moxfield."""
        deck_id = deck_id_or_url
        if "moxfield.com" in deck_id_or_url:
            deck_id = self.extract_deck_id(deck_id_or_url)
        
        if not deck_id:
            return None

        # Text export is usually less protected than API
        url = f"https://www.moxfield.com/decks/{deck_id}/export/text"
        text = self._get_html(url)
        
        if text and "Sideboard" in text:
            return self._parse_text_deck(text, deck_id)
        
        # Try API as second fallback
        print(f"Text export failed or empty for {deck_id}, trying API...")
        url = f"https://api.moxfield.com/v2/decks/all/{deck_id}"
        json_str = self._get_html(url)
        if json_str:
            try:
                data = json.loads(json_str)
                return self._simplify_deck(data)
            except:
                pass
        
        return None

    def _parse_text_deck(self, text, deck_id):
        """Parses a text-based decklist."""
        simplified = {
            "name": f"Deck {deck_id}",
            "author": "Unknown",
            "url": f"https://www.moxfield.com/decks/{deck_id}",
            "mainboard": [],
            "sideboard": []
        }
        
        is_sideboard = False
        for line in text.splitlines():
            line = line.strip()
            if not line:
                if simplified["mainboard"]:
                    is_sideboard = True
                continue
            
            if line.lower() == "sideboard":
                is_sideboard = True
                continue
            
            match = re.match(r'^(\d+)\s+(.+)$', line)
            if match:
                qty = int(match.group(1))
                name = match.group(2)
                item = {"name": name, "qty": qty, "type": ""}
                if is_sideboard:
                    simplified["sideboard"].append(item)
                else:
                    simplified["mainboard"].append(item)
        
        return simplified

    def _simplify_deck(self, data):
        """Simplifies the Moxfield API response."""
        simplified = {
            "name": data.get("name"),
            "author": data.get("createdByUser", {}).get("userName"),
            "url": f"https://www.moxfield.com/decks/{data.get('publicId')}",
            "mainboard": [],
            "sideboard": []
        }
        for card_name, details in data.get("mainboard", {}).items():
            simplified["mainboard"].append({"name": card_name, "qty": details.get("quantity", 1), "type": ""})
        for card_name, details in data.get("sideboard", {}).items():
            simplified["sideboard"].append({"name": card_name, "qty": details.get("quantity", 1), "type": ""})
        return simplified

if __name__ == "__main__":
    api = MoxfieldAPI()
    test_url = "https://www.moxfield.com/decks/1B83HomRAEqRt6oFZ70xxQ"
    deck = api.fetch_deck(test_url)
    if deck:
        print(f"Success! Fetched deck: {deck['name']}")
    else:
        print("Failed to fetch decklist.")
