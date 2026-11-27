"""Shrink the concept's receptacle to the bot socket's size and put the pin holes where the plug's pins are."""
from PIL import Image, ImageDraw, ImageFilter

CX, CY = 510, 785
S = 0.00036                      # panel metres per concept pixel (outlet_build.py)
K = 0.0328 / 205                 # receptacle metres per concept pixel: dark opening (205 px) = bot bore, 32.8 mm
F = K / S
im = Image.open("gpt-a.png").convert("RGB")

rec = im.crop((CX - 330, CY - 330, CX + 330, CY + 330))
d = ImageDraw.Draw(rec)
c = 330
for hx, hy in ((512, 705), (418, 845), (602, 845)):
    x, y = hx - CX + c, hy - CY + c
    d.ellipse((x - 46, y - 46, x + 46, y + 46), fill=(38, 30, 30))
for px, py in ((0, 0.012), (-0.0105, -0.006), (0.0105, -0.006)):   # pins, metres, y up
    x, y = c + px / K, c - py / K
    for r, col in ((0.0051 / K, (12, 9, 10)), (0.0047 / K, (128, 86, 72)), (0.0040 / K, (0, 0, 0))):
        d.ellipse((x - r, y - r, x + r, y + r), fill=col)
n = round(660 * F)
small = rec.resize((n, n), Image.LANCZOS)
mask = Image.new("L", (n * 4, n * 4), 0)
ImageDraw.Draw(mask).ellipse((0, 0, n * 4 - 1, n * 4 - 1), fill=255)   # the housing edge sits at 318 of 330 px
mask = mask.resize((n, n), Image.LANCZOS)

out = im.copy()
cover = Image.new("L", out.size, 0)
ImageDraw.Draw(cover).ellipse((CX - 345, CY - 345, CX + 345, CY + 345), fill=255)
# The face under the old receptacle (and its painted shadow), filled row by row between the face just
# outside that shadow on either side, so the fill meets the surrounding face without a seam.
import math
R = 368
fill = Image.new("RGB", out.size)
for y in range(CY - R + 1, CY + R):
    h = math.sqrt(R * R - (y - CY) ** 2)
    xl, xr = max(166, round(CX - h)), min(2 * CX - 166, round(CX + h))   # stay inside the face, off the frame bevel
    a, b = im.getpixel((xl, y)), im.getpixel((xr, y))
    for x in range(xl, xr + 1):
        t = (x - xl) / max(1, xr - xl)
        fill.putpixel((x, y), tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3)))
out.paste(fill, (0, 0), cover.filter(ImageFilter.GaussianBlur(10)))   # feathered so no seam shows
out.paste(small, (round(CX - n / 2), round(CY - n / 2)), mask)
out.save("outlet_tex.png")
print("scale", round(F, 4), "patch", n, "radii px: disc", round(247 * F, 1), "ring", round(290 * F, 1), "housing", round(318 * F, 1))
