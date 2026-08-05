# FitBiblia Texture Assets

Reusable texture assets derived from the operator's AI-generated raw textures
(`../raw/`). Built with pure Pillow (no ImageMagick / browser / sudo on this box).

Brand palette (LOCKED): Gyűrött arany `#C9A227` · Antracit `#2A2D31` ·
Fekete `#121212` · Csont `#EFE7D8` · Matt sötétbordó `#6E2433`.
Highlight rule: GOLD = positive / CTA, DARK BORDEAUX = negative / warning,
bone + glass = neutral.

## Sources chosen
- **Best gold foil = `../raw/10.jpg`** — richest metallic warm gold, even tone,
  strong specular highlights, consistent crumple.
- **Best frosted glass = `../raw/09.jpg`** — clean, soft, evenly diffused,
  neutral-cool, and the only glass shot with **no watermark**.

> Note: every gold raw carries an "AI-Generated" watermark in the top-right
> corner. All gold crops here are taken from lower / central regions that avoid
> that corner, so the assets are watermark-free.

## Assets

| File | Dim | Mode | Source | Purpose |
|------|-----|------|--------|---------|
| `cta-bar-gold.png`     | 1600×400 | P (256) | raw/10 | Horizontal gold-foil CTA / highlight bar, evenly toned. |
| `gold-tile-256.png`    | 256×256  | RGB     | raw/10 | Small seamless-ish gold swatch for tiling backgrounds / washes. |
| `gold-frame-rect.png`  | 1200×800 | P+α     | raw/10 | Rounded-rect gold contour frame, transparent center. |
| `gold-frame-circle.png`| 800×800  | P+α     | raw/10 | Circular gold ring frame, transparent center. |
| `glass-panel.png`      | 1200×800 | RGBA    | raw/09 | Frosted translucent panel, real alpha ≈0.70, rounded corners. |

All PNGs are optimized and < 500 KB. Gold assets are palette-quantized
(FASTOCTREE) — gold's narrow gamut tolerates it with no visible loss.

## Using them — `overlay.py`

The compositor lives one level up: `../overlay.py` (pure Python + Pillow,
importable). `<base>` may be an image path **or** a `WxH` spec (e.g. `1080x1350`)
which synthesizes a blank Csont-white canvas — handy for PDF-page-sized work
without a browser.

```bash
# Rich gold wash over a slide (multiply, 55%)
python3 ../overlay.py slide.png gold-tile-256.png out.png --mode multiply --opacity 0.55

# Drop the frosted glass panel (uses its baked alpha) centered on a base
python3 ../overlay.py slide.png glass-panel.png out.png --panel

# Gold texture clipped to a circle, screened on top (badge)
python3 ../overlay.py slide.png gold-tile-256.png badge.png --mode screen --mask circle --opacity 0.8

# Synthesize a 1080x1350 bone canvas and lay the glass panel on it
python3 ../overlay.py 1080x1350 glass-panel.png card.png --panel
```

CLI: `python3 ../overlay.py <base> <texture> <out> [--mode multiply|overlay|screen|normal] [--opacity 0.0-1.0] [--mask rect|circle] [--panel]`

Import API:
```python
from overlay import composite, panel, load_base
```

## Off-spec raws to consider regenerating
- `08.jpg` — glass, but covered in water droplets (condensation), not a clean
  frosted panel. Usable only if a "wet glass" look is wanted.
- `11.jpg` — glass, but almost featureless / too plain; watermarked.
- `12.jpg` — gold, watermark-free but darker and non-square (1280×853); kept in
  reserve as a watermark-free alternative to raw/10.
- `05.jpg`, `06.jpg` — gold with uneven vignette in corners.
