
import base64
import os
import json

d = 'assets/mana_symbols'
files = {
    'W': 'mana_W_128.webp',
    'U': 'mana_U_128.webp',
    'B': 'mana_B_128.webp',
    'R': 'mana_R_128.webp',
    'G': 'mana_G_128.webp'
}

results = {}
for color, filename in files.items():
    path = os.path.join(d, filename)
    if os.path.exists(path):
        with open(path, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode()
            results[color] = b64

with open('mana_b64.json', 'w') as out:
    json.dump(results, out)
print("Done. Saved to mana_b64.json")
