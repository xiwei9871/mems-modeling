"""Generate the solder-mask surface texture for the M3BW mainboard.

Deterministic (seeded) PIL drawing: mottled green mask, dark/light traces,
gold vias, component pads + silkscreen outlines from scripts/pcb_layout.py,
then a clean border. Output: assets/pcb_surface.png

Run: .venv/bin/python scripts/generate_pcb_texture.py
"""
from __future__ import annotations

import os
import random
import sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from pcb_layout import BOARD, COMPONENTS, MOUNT_HOLES, PASSIVE_ZONES

PX_PER_CM = 150.0
W = int(round(BOARD["x"] * PX_PER_CM))   # 780
H = int(round(BOARD["y"] * PX_PER_CM))   # 1110
BORDER = 18
SEED = 0x3B17

BASE = (24, 110, 40)
TRACE_DARK = (14, 84, 27)
TRACE_LIGHT = (44, 140, 54)
VIA_GOLD = (176, 148, 70)
PAD_GOLD = (198, 168, 80)
SILK = (212, 220, 208)


def cm(x, y):
    """board cm (origin center, +y up) -> pixel (origin top-left, +y down)."""
    return ((x + BOARD["x"] / 2) * PX_PER_CM, (BOARD["y"] / 2 - y) * PX_PER_CM)


def footprint_rect(c):
    if c["type"] in ("sma",):
        s = 0.95 / 2
        return c["pos"][0] - s, c["pos"][1] - s, c["pos"][0] + s, c["pos"][1] + s
    if c["type"] in ("jst", "jst_sm"):
        return c["pos"][0] - 0.4, c["pos"][1] - 0.35, c["pos"][0] + 0.4, c["pos"][1] + 0.35
    w, d = c["size"][0], c["size"][1]
    return c["pos"][0] - w / 2, c["pos"][1] - d / 2, c["pos"][0] + w / 2, c["pos"][1] + d / 2


def pad(draw, x, y, w, h):
    cx, cy = cm(x, y)
    hw, hh = w * PX_PER_CM / 2, h * PX_PER_CM / 2
    draw.rectangle([cx - hw, cy - hh, cx + hw, cy + hh], fill=PAD_GOLD)


def pads_for(draw, c):
    x0, y0, x1, y1 = footprint_rect(c)
    t = c["type"]
    if t == "qfp":
        # 4 sides of fine pitch pads
        n = c.get("pins", 25)
        for i in range(n):
            f = (i + 0.5) / n
            pad(draw, x0 - 0.12, y0 + f * (y1 - y0), 0.22, 0.045)
            pad(draw, x1 + 0.12, y0 + f * (y1 - y0), 0.22, 0.045)
            pad(draw, x0 + f * (x1 - x0), y0 - 0.12, 0.045, 0.22)
            pad(draw, x0 + f * (x1 - x0), y1 + 0.12, 0.045, 0.22)
    elif t == "module":
        n = 12
        for i in range(n):
            f = (i + 0.5) / n
            pad(draw, x0 + f * (x1 - x0), y0 - 0.06, 0.10, 0.16)
            pad(draw, x0 + f * (x1 - x0), y1 + 0.06, 0.10, 0.16)
    elif t in ("ic", "sot223", "xtal", "block"):
        n = max(3, int((y1 - y0) / 0.2))
        for i in range(n):
            f = (i + 0.5) / n
            pad(draw, x0 - 0.08, y0 + f * (y1 - y0), 0.14, 0.05)
            pad(draw, x1 + 0.08, y0 + f * (y1 - y0), 0.14, 0.05)
    elif t in ("jst", "jst_sm"):
        np_ = c.get("pins", 4)
        for i in range(np_):
            pad(draw, x0 + 0.15 + i * ((x1 - x0 - 0.3) / max(np_ - 1, 1)), y1 + 0.05, 0.07, 0.12)
    elif t == "sma":
        for sx in (-0.42, 0.42):
            for sy in (-0.42, 0.42):
                pad(draw, c["pos"][0] + sx, c["pos"][1] + sy, 0.16, 0.16)


def main():
    img = Image.new("RGB", (W, H), BASE)
    d = ImageDraw.Draw(img)
    rng = random.Random(SEED)

    # mottle
    for _ in range(3200):
        x = rng.uniform(BORDER, W - BORDER)
        y = rng.uniform(BORDER, H - BORDER)
        delta = rng.randint(-8, 8)
        d.point((x, y), fill=tuple(max(0, min(255, c + delta)) for c in BASE))

    # traces
    for _ in range(640):
        x = rng.uniform(BORDER + 6, W - BORDER - 6)
        y = rng.uniform(BORDER + 6, H - BORDER - 6)
        color = TRACE_DARK if rng.random() < 0.7 else TRACE_LIGHT
        width = 2 if rng.random() < 0.85 else 3
        for _ in range(rng.randint(2, 5)):
            ln = rng.uniform(20, 150)
            horiz = rng.random() < 0.5
            sgn = 1.0 if rng.random() < 0.5 else -1.0
            x2 = x + sgn * ln if horiz else x
            y2 = y if horiz else y + sgn * ln
            x2 = min(max(x2, BORDER), W - BORDER)
            y2 = min(max(y2, BORDER), H - BORDER)
            d.line([(x, y), (x2, y2)], fill=color, width=width)
            x, y = x2, y2

    # vias
    for _ in range(950):
        x = rng.uniform(BORDER + 4, W - BORDER - 4)
        y = rng.uniform(BORDER + 4, H - BORDER - 4)
        r = rng.uniform(0.9, 1.8)
        d.ellipse([x - r, y - r, x + r, y + r], fill=VIA_GOLD)

    # component pads + silkscreen outlines
    for c in COMPONENTS:
        pads_for(d, c)
        x0, y0, x1, y1 = footprint_rect(c)
        g = 0.18
        p0 = cm(x0 - g, y1 + g)
        p1 = cm(x1 + g, y0 - g)
        d.rectangle([p0, p1], outline=SILK, width=1)

    # mounting holes: plated rings + keep-out circle
    for hx, hy in MOUNT_HOLES:
        cx, cy = cm(hx, hy)
        d.ellipse([cx - 5.4, cy - 5.4, cx + 5.4, cy + 5.4], fill=PAD_GOLD)
        d.ellipse([cx - 3.4, cy - 3.4, cx + 3.4, cy + 3.4], fill=BASE)
        d.ellipse([cx - 5.4, cy - 5.4, cx + 5.4, cy + 5.4], outline=SILK, width=1)

    # silkscreen labels
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 13)
        font_big = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
    except Exception:
        font = font_big = ImageFont.load_default()
    for c in COMPONENTS:
        x0, y0, x1, y1 = footprint_rect(c)
        lx, ly = cm(x0, y1 + 0.28)
        d.text((lx - 6, ly - 5), c["id"].split("_", 1)[-1], fill=SILK, font=font)
    # board marking, vertical along +x side (as on the real board)
    txt = Image.new("RGBA", (420, 30), (0, 0, 0, 0))
    ImageDraw.Draw(txt).text((4, 4), "LKRL_DL_MB-M3BW_A0", fill=SILK + (255,), font=font_big)
    txt = txt.rotate(-90, expand=True)
    tcx, tcy = cm(1.35, -1.9)
    img.paste(txt, (int(tcx - txt.width / 2), int(tcy - txt.height / 2)), txt)
    for _ in range(60):
        x = rng.uniform(BORDER + 8, W - BORDER - 30)
        y = rng.uniform(BORDER + 8, H - BORDER - 8)
        d.line([(x, y), (x + rng.uniform(8, 26), y)], fill=SILK, width=1)

    # clean border
    d.rectangle([0, 0, W, BORDER], fill=BASE)
    d.rectangle([0, H - BORDER, W, H], fill=BASE)
    d.rectangle([0, 0, BORDER, H], fill=BASE)
    d.rectangle([W - BORDER, 0, W, H], fill=BASE)

    out = os.path.join(ROOT, "assets", "pcb_surface.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.save(out)
    print("wrote", out, img.size)


if __name__ == "__main__":
    main()
