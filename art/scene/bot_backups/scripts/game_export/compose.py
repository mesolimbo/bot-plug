"""Combine the bake passes: colour x (soft light, ambient occlusion, crevice grime), decals on top, glow left unshaded."""
import numpy as np
from PIL import Image

S = 4096
def load(n, size=S, grey=False):
    im = Image.open(f"bg_{n}.png").convert("L" if grey else "RGB")
    if im.size[0] != size:
        im = im.resize((size, size), Image.BILINEAR)
    return np.asarray(im, np.float32) / 255

ao, lit, emit = load("ao", grey=True), load("lit", grey=True), load("emit", grey=True)
dcol, da = load("dec_col"), load("dec_a", grey=True)
lit = np.clip(lit / max(np.percentile(lit[lit > 0.02], 95), 1e-3), 0, 1.15)
shade = (0.66 + 0.34 * lit) * (0.5 + 0.5 * ao)
grime = np.clip((0.82 - ao) / 0.5, 0, 1)[..., None] * 0.35
glow = np.clip(emit * 4, 0, 1)[..., None]
for kind in ("on", "off"):
    c = load("col_" + kind)
    c = c * (1 - da[..., None]) + dcol * da[..., None]
    f = c * shade[..., None]
    f = f * (1 - grime) + f * np.array([0.80, 0.72, 0.60]) * grime
    if kind == "on":
        f = f * (1 - glow) + c * glow
    else:  # screen face is part of the colour pass; keep its own brightness too
        f = f * (1 - glow) + c * glow
    out = Image.fromarray((np.clip(f, 0, 1) * 255 + 0.5).astype(np.uint8))
    out.save(f"bot_{kind}.jpg", quality=90, optimize=True)
    print(kind, "ok")
