from __future__ import annotations
import json, hashlib
from pathlib import Path
from typing import Any
from PIL import Image, ImageDraw, ImageFont, ImageOps

BONE = '#EEE5CF'
CANVAS = (1080, 1350)

class RenderError(RuntimeError):
    pass

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def load_manifest(root: Path) -> dict[str, Any]:
    manifest = json.loads((root / 'asset_manifest.json').read_text(encoding='utf-8'))
    for key, spec in manifest['assets'].items():
        p = root / 'assets' / spec['relative_path']
        if not p.exists():
            raise RenderError(f'ASSET_REQUIRED:{key}')
        if sha256(p) != spec['sha256']:
            raise RenderError(f'ASSET_HASH_MISMATCH:{key}')
    return manifest

def cover_crop(img: Image.Image, size=CANVAS) -> Image.Image:
    return ImageOps.fit(img.convert('RGB'), size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))

def font(root: Path, which: str, size: int):
    rel = {
        'regular': 'instrument_sans/static/InstrumentSans-Regular.ttf',
        'semibold': 'instrument_sans/static/InstrumentSans-SemiBold.ttf',
        'hook': 'Fraunces-Italic.ttf',
    }[which]
    return ImageFont.truetype(str(root / 'assets' / rel), size=size)

def wrap(draw, text, fnt, max_width):
    words = text.split(); lines = []; current = ''
    for word in words:
        test = word if not current else current + ' ' + word
        if draw.textbbox((0, 0), test, font=fnt)[2] <= max_width:
            current = test
        else:
            if current: lines.append(current)
            current = word
    if current: lines.append(current)
    return lines

def draw_text_block(draw, xy, text, fnt, fill=BONE, max_width=888, line_gap=12, anchor='la'):
    lines = wrap(draw, text, fnt, max_width); y = xy[1]
    for line in lines:
        draw.text((xy[0], y), line, font=fnt, fill=fill, anchor=anchor)
        bbox = draw.textbbox((xy[0], y), line, font=fnt, anchor=anchor)
        y += (bbox[3] - bbox[1]) + line_gap
    return y, lines

def foil_text(base, root, text, center, font_size, max_width=900):
    if text != text.lower():
        raise RenderError('GOLD_HOOK_NOT_LOWERCASE')
    f = font(root, 'hook', font_size)
    probe = Image.new('L', (1600, 500), 0); d = ImageDraw.Draw(probe)
    bbox = d.textbbox((0, 0), text, font=f)
    w, h = bbox[2] - bbox[0] + 20, bbox[3] - bbox[1] + 20
    mask = Image.new('L', (w, h), 0); md = ImageDraw.Draw(mask)
    md.text((10 - bbox[0], 10 - bbox[1]), text, font=f, fill=255)
    mask = mask.resize((int(mask.width * 1.23), mask.height), Image.Resampling.LANCZOS)
    if mask.width > max_width:
        scale = max_width / mask.width
        mask = mask.resize((max_width, max(1, int(mask.height * scale))), Image.Resampling.LANCZOS)
    foil = ImageOps.fit(Image.open(root / 'assets/gold_foil.jpg').convert('RGB'), mask.size, method=Image.Resampling.LANCZOS)
    x, y = int(center[0] - mask.width / 2), int(center[1] - mask.height / 2)
    base.paste(foil, (x, y), mask)

def paste_logo(base, root, width=150, y=1230):
    logo = Image.open(root / 'assets/logo.png').convert('RGBA')
    logo = logo.crop(logo.getbbox())
    ratio = width / logo.width
    logo = logo.resize((width, int(logo.height * ratio)), Image.Resampling.LANCZOS)
    base.alpha_composite(logo, ((base.width - width) // 2, y - logo.height // 2))

def chevron(draw, x=1025, y=675, size=28, width=6):
    draw.line([(x-size//2, y-size), (x+size//2, y), (x-size//2, y+size)], fill=BONE, width=width, joint='curve')

def density_guard(spec):
    role = spec.get('role', 'INNER_EXPLAIN')
    body = (spec.get('body') or '').strip(); headline = (spec.get('headline') or '').strip()
    max_chars = 350 if role != 'COVER' else 130
    if len(body) + len(headline) > max_chars:
        raise RenderError('COPY_DENSITY_CONFLICT')

def render_slide(spec, root: Path, is_last=False):
    density_guard(spec)
    base = cover_crop(Image.open(root / 'assets/background.jpg')).convert('RGBA')
    draw = ImageDraw.Draw(base)
    role = spec.get('role', 'INNER_EXPLAIN')
    headline = (spec.get('headline') or '').strip(); body = (spec.get('body') or '').strip(); hook = (spec.get('hook') or '').strip()
    if role == 'COVER':
        if headline:
            _, lines = draw_text_block(draw, (540, 330), headline, font(root, 'semibold', 58), max_width=850, line_gap=8, anchor='ma')
            if len(lines) > 3: raise RenderError('COPY_DENSITY_CONFLICT')
        if hook: foil_text(base, root, hook, (540, 640), 150, 900)
        if body: draw_text_block(draw, (540, 820), body, font(root, 'regular', 34), max_width=760, line_gap=8, anchor='ma')
    elif role == 'INSIGHT_WHISPER':
        if headline: draw_text_block(draw, (540, 460), headline, font(root, 'semibold', 44), max_width=760, line_gap=8, anchor='ma')
        if body: draw_text_block(draw, (540, 665), body, font(root, 'regular', 31), max_width=760, line_gap=11, anchor='ma')
        if hook: foil_text(base, root, hook, (540, 850), 92, 760)
    elif role == 'CTA':
        if headline: draw_text_block(draw, (540, 480), headline, font(root, 'semibold', 48), max_width=790, line_gap=9, anchor='ma')
        if body: draw_text_block(draw, (540, 680), body, font(root, 'regular', 31), max_width=760, line_gap=10, anchor='ma')
    else:
        if headline: draw_text_block(draw, (540, 365), headline, font(root, 'semibold', 43), max_width=820, line_gap=8, anchor='ma')
        if body:
            y, _ = draw_text_block(draw, (540, 555), body, font(root, 'regular', 31), max_width=820, line_gap=11, anchor='ma')
            if y > 1070: raise RenderError('COPY_DENSITY_CONFLICT')
        if hook: foil_text(base, root, hook, (540, 900), 88, 720)
    if role != 'COVER': paste_logo(base, root)
    if not is_last: chevron(draw)
    return base.convert('RGB')

def render_carousel(job, root: Path, out_dir: Path):
    manifest = load_manifest(root)
    slides = job.get('slides') or []
    if not slides: raise RenderError('SERIES_INCOMPLETE')
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for i, spec in enumerate(slides, 1):
        if spec.get('slide_number', i) != i: raise RenderError('SERIES_INCOMPLETE')
        img = render_slide(spec, root, is_last=(i == len(slides)))
        path = out_dir / f'slide_{i:02d}.png'; img.save(path, 'PNG', optimize=True); outputs.append(str(path))
    result = {'renderer_version':'1.0.0','expected_slides':len(slides),'rendered_slides':len(outputs),'outputs':outputs,'asset_manifest_version':manifest['version']}
    (out_dir / 'render_manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result
