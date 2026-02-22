"""Generates src/bg_data.py with base64-encoded background image."""
import base64, pathlib

root = pathlib.Path(__file__).parent.parent
img_path = root / "assets" / "bg.jpg"
out_path = root / "src" / "bg_data.py"

b64 = base64.b64encode(img_path.read_bytes()).decode()
out_path.write_text(f'BG_IMAGE_B64 = "{b64}"\n')
print(f"Written {len(b64)} chars to {out_path}")
