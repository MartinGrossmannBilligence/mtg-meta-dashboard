import json
import urllib.request
import sys

def dump_spicerack_data(days, filename):
    url = f"https://api.spicerack.gg/api/export-decklists/?event_format=Premodern&num_days={days}"
    print(f"Fetching from {url}...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"Successfully dumped data to {filename}")
            print(f"Total tournaments: {len(data)}")
            if len(data) > 0:
                first_t = data[0]
                print(f"First tournament keys: {list(first_t.keys())}")
                if 'standings' in first_t and len(first_t['standings']) > 0:
                    first_s = first_t['standings'][0]
                    print(f"First standing keys: {list(first_s.keys())}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    days = 30
    if len(sys.argv) > 1:
        days = int(sys.argv[1])
    dump_spicerack_data(days, "spicerack_dump.json")
