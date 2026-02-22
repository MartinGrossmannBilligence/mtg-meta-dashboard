"""Regenerates src/bg_data.py with higher visibility (50% alpha)."""
import base64, pathlib
from PIL import Image

root = pathlib.Path(__file__).parent.parent
img_path = root / "assets" / "bg.jpg"
src_path = root.parent / ".gemini" / "antigravity" / "brain" / "699dfad3-8429-4a34-8c9f-c66ce122260c" / "media__1771768264095.jpg"
if not src_path.exists():
    src_path = img_path

img = Image.open(src_path).convert("L")
img = img.resize((1600, 1200), Image.LANCZOS)
dark = Image.new("L", img.size, 24)
# 50% original = clearly visible but still dark
blended = Image.blend(dark, img, alpha=0.50)
blended.save(img_path, "JPEG", quality=85)

out_path = root / "src" / "bg_data.py"
b64 = base64.b64encode(img_path.read_bytes()).decode()
out_path.write_text(f'BG_IMAGE_B64 = "{b64}"\n')
print(f"Done: {len(b64)} chars")
