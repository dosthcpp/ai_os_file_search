import json

class AdaptiveUIEngine:
    """Simulates KR20160097974A: UI color conversion based on image Representative Color"""
    
    def extract_representative_color(self, image_metadata: dict):
        # In a real scenario, we'd use k-means on pixel data
        # Here we simulate with image metadata
        dominant = image_metadata.get("dominant_rgb", (255, 255, 255))
        return dominant

    def generate_adaptive_palette(self, rgb: tuple):
        r, g, b = rgb
        # Calculate contrast text color (W3C standard)
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        text_color = "black" if brightness > 128 else "white"
        
        # Highlight color (complementary)
        highlight = (255-r, 255-g, 255-b)
        
        return {
            "background": f"rgb{rgb}",
            "text": text_color,
            "button_primary": f"rgb{highlight}",
            "overlay_opacity": 0.7 if brightness < 100 else 0.4
        }

if __name__ == "__main__":
    engine = AdaptiveUIEngine()
    
    # Case: Night City Image (Dark Blue)
    image_info = {"dominant_rgb": (20, 24, 82)}
    palette = engine.generate_adaptive_palette(engine.extract_representative_color(image_info))
    
    print("--- Dark Theme Adaptive Palette ---")
    print(json.dumps(palette, indent=2))
    
    # Case: Beach Image (Light Yellow/Blue)
    image_info_2 = {"dominant_rgb": (240, 230, 180)}
    palette_2 = engine.generate_adaptive_palette(engine.extract_representative_color(image_info_2))
    
    print("\n--- Light Theme Adaptive Palette ---")
    print(json.dumps(palette_2, indent=2))
