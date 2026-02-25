
from PIL import Image, ImageOps, ImageDraw
import base64
import os
import io

def crop_mana_symbols(image_path, output_dir):
    img = Image.open(image_path).convert("RGBA")
    width, height = img.size
    
    # Assuming 5 symbols in a row: W, U, B, R, G
    symbol_width = width // 5
    
    symbols = ['W', 'U', 'B', 'R', 'G']
    results = {}
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    for i, symbol in enumerate(symbols):
        left = i * symbol_width
        top = 0
        right = (i + 1) * symbol_width
        bottom = height
        
        # Crop the symbol
        crop = img.crop((left, top, right, bottom))
        
        # Make it a square/circle
        size = min(crop.size)
        # Center crop to square
        left_s = (crop.width - size) // 2
        top_s = (crop.height - size) // 2
        crop = crop.crop((left_s, top_s, left_s + size, top_s + size))
        
        # Create circular mask
        mask = Image.new('L', (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)
        
        # Apply mask
        output = ImageOps.fit(crop, (size, size), centering=(0.5, 0.5))
        output.putalpha(mask)
        
        # Save
        save_path = os.path.join(output_dir, f"mana_{symbol}.png")
        output.save(save_path, "PNG")
        
        # Get base64
        buffered = io.BytesIO()
        output.save(buffered, format="PNG")
        results[symbol] = base64.b64encode(buffered.getvalue()).decode()
        
    return results

if __name__ == "__main__":
    source = "input_file_0.png"
    if os.path.exists(source):
        print(f"Processing {source}...")
        res = crop_mana_symbols(source, "assets/mana_symbols")
        for s, b64 in res.items():
            print(f"'{s}': '{b64}',") # Print full b64 for easy copying
    else:
        print(f"Error: {source} not found.")
        # Fallback to searching
        import glob
        images = glob.glob("*.png") + glob.glob("*.jpg")
        print(f"Available images: {images}")
