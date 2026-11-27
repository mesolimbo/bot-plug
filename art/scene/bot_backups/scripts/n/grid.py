import sys
from PIL import Image, ImageDraw
src, out, lon0, lon1, lat0, lat1, scale = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]), float(sys.argv[6]), float(sys.argv[7])
im = Image.open(src).convert("RGB"); W, H = im.size
# allow wrap: tile horizontally
big = Image.new("RGB", (W * 3, H)); [big.paste(im, (k * W, 0)) for k in range(3)]
def X(lon): return W + (lon / 360 + 0.5) * W
def Y(lat): return (0.5 - lat / 180) * H
box = (int(X(lon0)), int(Y(lat1)), int(X(lon1)), int(Y(lat0)))
cr = big.crop(box); cr = cr.resize((int(cr.width * scale), int(cr.height * scale)), Image.LANCZOS)
d = ImageDraw.Draw(cr)
step = 10
import math
l = math.ceil(lon0 / step) * step
while l <= lon1:
    x = (X(l) - box[0]) * scale; d.line([(x, 0), (x, cr.height)], fill=(0, 200, 255) if l % 30 else (255, 0, 200), width=1); d.text((x + 2, 2), str(int(((l + 180) % 360) - 180)), fill=(255, 0, 0)); l += step
l = math.ceil(lat0 / step) * step
while l <= lat1:
    y = (Y(l) - box[1]) * scale; d.line([(0, y), (cr.width, y)], fill=(0, 200, 255) if l % 30 else (255, 0, 200), width=1); d.text((2, y + 2), str(int(l)), fill=(255, 0, 0)); l += step
cr.save(out)
