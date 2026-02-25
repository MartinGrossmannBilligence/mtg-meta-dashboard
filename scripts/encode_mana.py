
import base64
import os

d = 'assets/mana_symbols'
files = {
    'W': 'mana_W_128.webp',
    'U': 'mana_U_128.webp',
    'B': 'mana_B_128.webp',
    'R': 'mana_R_128.webp',
    'G': 'mana_G_128.webp'
}

for color, filename in files.items():
    path = os.path.join(d, filename)
    if os.path.exists(path):
        with open(path, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode()
            print(f"'{color}': '{b64}',")
    else:
        print(f"Error: {path} not found")
