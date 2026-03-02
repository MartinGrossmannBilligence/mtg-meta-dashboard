import requests
import sys
import json
import re

def test_fetch(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        
        # Find __NEXT_DATA__
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', response.text, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
            with open("spicerack_data_sample.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print("Successfully extracted __NEXT_DATA__ to spicerack_data_sample.json")
            
            # Print a bit of the structure
            props = data.get("props", {})
            pageProps = props.get("pageProps", {})
            print(f"pageProps keys: {list(pageProps.keys())}")
        else:
            print("Could not find __NEXT_DATA__")
            with open("spicerack_raw.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            print("Saved raw HTML to spicerack_raw.html")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_fetch(sys.argv[1])
    else:
        test_fetch("https://spicerack.gg/events/decklists?format=premodern")
