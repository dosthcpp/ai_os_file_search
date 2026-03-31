import json
import math
from pathlib import Path

# Pillow is used to extract the dominant color from a real image.
# It is an optional dependency; if missing, a simulation fallback is used.
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def extract_dominant_color(image_path: str) -> tuple[int, int, int]:
    """
    Extract the dominant (most-frequent quantized) color from an image using Pillow.

    The image is resized to a small thumbnail before quantization to reduce noise
    and speed up processing — consistent with the patent's "region sampling" concept.

    Falls back to a simulated neutral grey if:
      - Pillow is not installed, or
      - the specified file does not exist.

    Returns an (R, G, B) tuple in the 0-255 range.
    """
    path = Path(image_path)

    if not PIL_AVAILABLE:
        print(f"[WARN] Pillow not installed — simulating dominant color for '{image_path}'")
        return (128, 128, 128)  # neutral grey simulation

    if not path.exists():
        print(f"[WARN] Image not found: '{image_path}' — simulating dominant color")
        return (128, 128, 128)  # neutral grey simulation

    with Image.open(path) as img:
        # Convert to RGB to discard alpha channel if present
        img = img.convert("RGB")

        # Resize to a small thumbnail to reduce quantization noise
        img.thumbnail((64, 64))

        # Quantize to 8 colors; the first palette entry is the most dominant
        quantized = img.quantize(colors=8)
        palette   = quantized.getpalette()  # flat list: [R,G,B, R,G,B, ...]

        # Count pixel occurrences per palette index
        pixel_counts = quantized.getcolors()  # list of (count, index)
        if not pixel_counts:
            return (palette[0], palette[1], palette[2])

        dominant_index = max(pixel_counts, key=lambda x: x[0])[1]
        r = palette[dominant_index * 3]
        g = palette[dominant_index * 3 + 1]
        b = palette[dominant_index * 3 + 2]
        return (r, g, b)


class SamsungAdaptiveUI:
    """
    PoC for KR20160097974A: Adaptive UI based on Image Color and Euclidean Distance.

    Workflow:
      1. Extract the dominant color from an image (representative color).
      2. Compare it against UI object base colors using Euclidean distance.
      3. If the colors are too similar (collision risk), substitute with a
         recommended accessible palette entry.
    """

    def __init__(self, threshold: int = 50):
        self.threshold = threshold
        # Predefined recommended palettes keyed by background luminance class
        self.recommendations = {
            "dark_bg":   {"text": "#FFFFFF", "button": "#4A90E2", "icon": "#F5A623"},
            "bright_bg": {"text": "#000000", "button": "#D0021B", "icon": "#417505"},
        }

    def calculate_distance(self, c1: tuple, c2: tuple) -> float:
        """[Equation 1] Euclidean color distance in RGB space."""
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2)))

    def apply_color_conversion(
        self,
        representative_rgb: tuple[int, int, int],
        object_base_rgb: tuple[int, int, int],
    ) -> dict:
        """
        Apply the patent's color-conversion logic.

        Args:
            representative_rgb: Dominant color extracted from the image.
            object_base_rgb:    Current base color of a UI element (text, icon, etc.).

        Returns:
            A dict with distance, similarity status, and the final UI palette.
        """
        r1, g1, b1 = representative_rgb

        distance   = self.calculate_distance(representative_rgb, object_base_rgb)
        is_similar = distance <= self.threshold

        # BT.709 luma weighting for the representative color
        luma  = 0.2126 * r1 + 0.7152 * g1 + 0.0722 * b1
        theme = "bright_bg" if luma > 128 else "dark_bg"

        return {
            "representative_color": representative_rgb,
            "object_base_color":    object_base_rgb,
            "color_distance":       round(distance, 2),
            "similarity_status":    "HIGH (Collision Risk)" if is_similar else "LOW (Safe)",
            "final_ui_palette": (
                self.recommendations[theme]
                if is_similar
                else {"text": "black" if luma > 128 else "white", "bg_luma": round(luma, 2)}
            ),
        }

    def run_from_image(
        self,
        image_path: str,
        object_base_rgb: tuple[int, int, int],
    ) -> dict:
        """
        Full pipeline: extract dominant color from image, then apply color conversion.

        Args:
            image_path:      Path to the source image (simulated if missing).
            object_base_rgb: Current UI element color to evaluate.
        """
        print(f"[PIL] Extracting dominant color from: {image_path}")
        representative_rgb = extract_dominant_color(image_path)
        print(f"[PIL] Dominant color: RGB{representative_rgb}")
        return self.apply_color_conversion(representative_rgb, object_base_rgb)


if __name__ == "__main__":
    ui = SamsungAdaptiveUI(threshold=100)

    # --- Case 1: Use Pillow to extract dominant color from an image ---
    print("--- Case 1: Dominant Color Extracted from Image (or Simulated) ---")
    result1 = ui.run_from_image(
        image_path="sample_wallpaper.jpg",   # will simulate if file is absent
        object_base_rgb=(40, 40, 40),         # dark text color to evaluate
    )
    print(json.dumps(result1, indent=2))

    # --- Case 2: High Similarity — hardcoded representative color ---
    print("\n--- Case 2: High Similarity (Camouflage Risk) ---")
    bg   = (30, 30, 30)   # dark grey background
    text = (40, 40, 40)   # similar dark grey text
    print(json.dumps(ui.apply_color_conversion(bg, text), indent=2))

    # --- Case 3: Low Similarity — good contrast ---
    print("\n--- Case 3: Low Similarity (Good Contrast) ---")
    bg_2   = (240, 240, 240)  # bright background
    text_2 = (20, 20, 20)     # dark text
    print(json.dumps(ui.apply_color_conversion(bg_2, text_2), indent=2))
