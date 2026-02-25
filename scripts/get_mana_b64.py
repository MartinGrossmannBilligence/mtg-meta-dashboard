
import base64
import os
import io
from PIL import Image

def get_b64(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# The mapping from Turn Turn context:
# input_file_0.png -> Black (Skull) - Wait, let me check the carousel order again.
# 1. Black (Skull)
# 2. Blue (Drop)
# 3. White (Sun)
# 4. Red (Fire)
# 5. Green (Tree)

files = ["input_file_0.png", "input_file_1.png", "input_file_2.png", "input_file_3.png", "input_file_4.png"]
colors = ['B', 'U', 'W', 'R', 'G']

results = {}
for i, f in enumerate(files):
    b64 = get_b64(f)
    if b64:
        results[colors[i]] = b64
    else:
        # Try parent directory
        b64 = get_b64(os.path.join("..", f))
        if b64:
            results[colors[i]] = b64

for c, b64 in results.items():
    print(f"'{c}': '{b64}',")
