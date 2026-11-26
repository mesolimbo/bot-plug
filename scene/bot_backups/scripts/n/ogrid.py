# overlay metric grid on an ortho render. args: src out ortho  hx hy vx vy  cx cy step [crop x0 y0 x1 y1 in world h,v] scale
# h axis label = world coord increasing to the right * sign
import sys
from PIL import Image, ImageDraw
src, out, ortho, hs, vs, ch, cv, step, scale = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]), float(sys.argv[6]), float(sys.argv[7]), float(sys.argv[8]), float(sys.argv[9])
# hs: sign of world h coordinate to the right (+1/-1); vs: sign of world v coord upward; ch,cv: world coords at image centre
im = Image.open(src).convert("RGB"); W, H = im.size
im = im.resize((int(W * scale), int(H * scale)), Image.LANCZOS); W, H = im.size
d = ImageDraw.Draw(im); ppm = W / ortho
import math
n = int(ortho / step) + 2
for k in range(-n, n + 1):
    wh = round((round(ch / step) + k) * step, 4)
    x = W / 2 + (wh - ch) * hs * ppm
    if 0 <= x < W:
        d.line([(x, 0), (x, H)], fill=(255, 0, 200) if abs(round(wh / step)) % 5 == 0 else (0, 200, 255), width=1); d.text((x + 2, 2), "%.2f" % wh, fill=(255, 0, 0)); d.text((x + 2, H - 12), "%.2f" % wh, fill=(255, 0, 0))
    wv = round((round(cv / step) + k) * step, 4)
    y = H / 2 - (wv - cv) * vs * ppm
    if 0 <= y < H:
        d.line([(0, y), (W, y)], fill=(255, 0, 200) if abs(round(wv / step)) % 5 == 0 else (0, 200, 255), width=1); d.text((2, y + 2), "%.2f" % wv, fill=(255, 0, 0)); d.text((W - 34, y + 2), "%.2f" % wv, fill=(255, 0, 0))
im.save(out)
