# Patent PoC 3 — Image Color Conversion & Adaptive UI (Samsung Patent)

## Invention Title
영상의 컬러 변환 방법 및 전자 장치
(Method for converting color of an image and an electronic device — KR20160097974A)

---

## Overview
This PoC simulates Samsung's patent for adaptive UI theming. The system extracts the **dominant color** from a source image using the Pillow library, then compares it to UI element colors using **Euclidean distance in RGB space**. If the colors are too similar (collision risk — e.g., dark text on a dark background), a recommended accessible palette is substituted automatically.

---

## Key Components

| Component | Role |
|---|---|
| `extract_dominant_color()` | Extracts the most-frequent quantized color from an image via Pillow |
| `SamsungAdaptiveUI` | Compares representative color against UI element colors and selects the final palette |

---

## Dominant Color Extraction (`extract_dominant_color`)

Uses the Pillow (`PIL`) library:

1. Open the image and convert to RGB (drops alpha channel).
2. Resize to a 64×64 thumbnail to reduce quantization noise.
3. Quantize to 8 colors.
4. Count pixel occurrences per palette index; select the most frequent entry.

**Fallback simulation**: If Pillow is not installed or the image file does not exist, the function returns a neutral grey `(128, 128, 128)` and logs a warning. This allows the PoC to run in environments without the library or a real image.

---

## Color Conversion Logic

```
D = sqrt((R1-R0)² + (G1-G0)² + (B1-B0)²)   ← Euclidean distance [Equation 1]

if D ≤ threshold:
    → HIGH similarity (collision risk)
    → Apply recommended accessible palette based on luma class

if D > threshold:
    → LOW similarity (safe contrast)
    → Keep object color as-is
```

BT.709 luma weighting is used to classify background brightness:
```
luma = 0.2126·R + 0.7152·G + 0.0722·B
```

---

## Recommended Palettes

| Theme | Text | Button | Icon |
|---|---|---|---|
| `dark_bg` (luma ≤ 128) | `#FFFFFF` | `#4A90E2` | `#F5A623` |
| `bright_bg` (luma > 128) | `#000000` | `#D0021B` | `#417505` |

---

## Usage

```bash
# With Pillow installed (pip install Pillow)
python poc_main.py

# Without Pillow — simulation fallback is used automatically
python poc_main.py
```

### Full Pipeline (image → dominant color → UI palette)
```python
ui = SamsungAdaptiveUI(threshold=100)
result = ui.run_from_image("wallpaper.jpg", object_base_rgb=(40, 40, 40))
```

---

## Dependencies
- Python 3.11+
- `Pillow` >= 10.0 (`pip install Pillow`) — optional; simulation fallback used if absent
