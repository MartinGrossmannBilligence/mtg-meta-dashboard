"""Regenerates src/bg_data.py - 30% brightness (between versions)."""
import base64, pathlib
from PIL import Image, ImageEnhance, ImageOps

root = pathlib.Path(__file__).parent.parent
img_path = root / "assets" / "bg.jpg"
src_path = root.parent / ".gemini" / "antigravity" / "brain" / "699dfad3-8429-4a34-8c9f-c66ce122260c" / "media__1771768264095.jpg"
if not src_path.exists():
    src_path = img_path

# Open and convert to grayscale - keep FULL resolution, no upscale crop
img = Image.open(src_path).convert("L")
# Scale to 1920x1440 keeping aspect ratio, NOT covering (contain mode)
img.thumbnail((1920, 1440), Image.LANCZOS)

# Auto-equalise to get full dynamic range
img = ImageOps.autocontrast(img, cutoff=2)

# 30% brightness - between too dark (0%) and too bright (40%)
enhancer = ImageEnhance.Brightness(img)
img = enhancer.enhance(0.30)

img.save(img_path, "JPEG", quality=80)

out_path = root / "src" / "bg_data.py"
b64 = base64.b64encode(img_path.read_bytes()).decode()
out_path.write_text(f'BG_IMAGE_B64 = "{b64}"\n')
print(f"Done: {len(b64)} chars, size: {img.size}")
