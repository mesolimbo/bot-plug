import json, os, sys
from PIL import Image, ImageDraw, ImageFont
V = os.path.join(os.path.dirname(os.path.abspath(__file__)), "v")
names = json.load(open(os.path.join(V, "junc_names.json")))
try:
    F = ImageFont.truetype("arial.ttf", 15)
except Exception:
    F = ImageFont.load_default()
cols = 6
S = 320
rows = (len(names) + cols - 1) // cols
sh = Image.new("RGB", (cols * S, rows * (S + 22)), (255, 255, 255))
d = ImageDraw.Draw(sh)
for i, n in enumerate(names):
    im = Image.open(os.path.join(V, "junc_%02d.png" % i)).convert("RGB").resize((S, S))
    x, y = (i % cols) * S, (i // cols) * (S + 22)
    sh.paste(im, (x, y + 22))
    d.text((x + 4, y + 3), "%d %s" % (i, n), fill=(0, 0, 0), font=F)
sh.save(os.path.join(V, "junctions.png"))
print(len(names))
