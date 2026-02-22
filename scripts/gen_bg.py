import base64, pathlib
from PIL import Image, ImageEnhance

root = pathlib.Path(__file__).parent.parent
img_path = root / "assets" / "bg.jpg"
src_path = pathlib.Path(r"C:\Users\MartinGrossmann\.gemini\antigravity\brain\699dfad3-8429-4a34-8c9f-c66ce122260c\media__1771780061697.jpg")

if not src_path.exists():
    raise FileNotFoundError(f"Image not found at {src_path}")

# Open and convert to RGB (Keep color)
img = Image.open(src_path).convert("RGB")
img.thumbnail((1920, 1440), Image.LANCZOS)

# 30% brightness (keeping color)
enhancer = ImageEnhance.Brightness(img)
img = enhancer.enhance(0.30)

img.save(img_path, "JPEG", quality=80)

out_path = root / "src" / "bg_data.py"
b64 = base64.b64encode(img_path.read_bytes()).decode()

# Using a REALLY unique variable name to bust cache on streamlit cloud
out_path.write_text(f'BG_BOP_V7_B64 = "{b64}"\n')
print(f"Done: {len(b64)} chars, size: {img.size}")
