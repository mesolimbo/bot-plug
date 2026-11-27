"""Blueprint v2: planned-part line drawings (hidden lines removed) over the old model's textured orthographic render.
SVG units: 1 px = 1 mm. PNGs are drawn at 2 px per mm."""
import base64, io, json, os
from PIL import Image, ImageDraw, ImageFont

BP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "blueprints")
lines = json.load(open(os.path.join(BP, "bp_lines.json")))
VIEWS = {"front": ((0, 1, 0), (0, 0, 1), (1, 0, 0)), "back": ((0, -1, 0), (0, 0, 1), (-1, 0, 0)),
         "side": ((-1, 0, 0), (0, 0, 1), (0, 1, 0)), "top": ((0, -1, 0), (1, 0, 0), (0, 0, 1))}
TITLE = {"front": "FRONT  (bot's left is on the right)", "back": "BACK", "side": "LEFT SIDE  (front of bot to the left)", "top": "TOP  (front of bot at the top)"}
COL = {"seam": (0, 70, 220), "part": (0, 0, 0), "light": (235, 120, 0), "vent": (140, 40, 190), "leg": (190, 20, 20), "core": (90, 90, 90)}
W, SC = 1100, 2
try:
    FONT = ImageFont.truetype("arial.ttf", 11 * SC); FONTB = ImageFont.truetype("arialbd.ttf", 15 * SC)
except Exception:
    FONT = FONTB = ImageFont.load_default()
# labels: text, 3D anchor (x, y, z), views, text offset (dx, dy) in mm on the sheet
Y = 0.1033
LABELS = [
    ("screen r136", (0.26, 0.0, 0.10), ["front"], (-28, -4)), ("bezel r139-169", (0.24, 0.105, 0.18), ["front"], (30, -40)),
    ("amber pill", (0.24, 0.148, 0.05), ["front"], (40, 10)), ("amber bar", (0.23, 0.0, -0.087), ["front"], (60, 40)),
    ("corner light", (0.2, 0.088, 0.228), ["front"], (60, -30)), ("brow panel", (0.2, 0.0, 0.243), ["front"], (-150, -40)),
    ("front grille: 4 ribs, 8 louvres", (0.17, 0.0, 0.275), ["front"], (-200, -60)), ("front grille", (0.17, 0.0, 0.275), ["top"], (120, -60)),
    ("rear grille: 3 ribs, 6 louvres", (-0.165, 0.0, 0.27), ["back"], (-230, -60)), ("rear grille", (-0.165, 0.0, 0.27), ["top"], (120, 60)),
    ("side slot", (-0.04, 0.165, 0.29), ["top"], (-170, 20)), ("side slot", (-0.04, 0.165, 0.285), ["side"], (40, -80)),
    ("dome r89", (-0.02, 0.0, 0.356), ["front", "back", "side"], (30, -30)), ("dome r89", (-0.02, 0.0, 0.356), ["top"], (150, 0)),
    ("toothed ring r123", (-0.02, -0.105, 0.322), ["top"], (150, -30)), ("collar + 2 lugs", (0.06, 0.125, 0.314), ["top"], (-190, -40)),
    ("antenna, tip z 499", (-0.0715, -0.153, 0.45), ["front", "back", "side"], (25, 0)), ("antenna boss", (-0.0715, -0.153, 0.31), ["top"], (120, 30)),
    ("leaf panel", (0.12, 0.2, 0.235), ["side"], (-110, -70)), ("shoulder panel", (-0.1, 0.2, 0.22), ["side"], (90, -70)),
    ("side panel", (0.02, 0.27, 0.06), ["side"], (-10, 0)), ("belt seam", (0.1, 0.22, 0.205), ["side"], (-200, -30)),
    ("cheek panel", (-0.2, 0.14, 0.03), ["back"], (-190, 10)), ("cheek panel", (-0.2, 0.14, 0.03), ["side"], (60, 30)),
    ("yellow chevron panel", (-0.21, 0.09, 0.2), ["back"], (-250, -20)), ("rear collar panel", (-0.2, 0.0, 0.225), ["back"], (140, -10)),
    ("dark lower panel", (-0.17, 0.07, -0.115), ["back"], (-230, 30)), ("socket housing 137 x 153", (-0.25, 0.05, 0.11), ["back"], (130, -10)),
    ("socket ring r37 + cloverleaf, centre z 30", (-0.25, 0.036, 0.03), ["back"], (130, 10)), ("3 LEDs", (-0.25, 0.015, 0.082), ["back"], (140, -30)),
    ("hinged dust cover r40 (open)", (-0.245, 0.03, -0.07), ["back"], (130, 30)), ("dust cover (open) + hinge", (-0.245, 0.0, -0.08), ["side"], (40, 40)),
    ("bib seam", (0.2, 0.135, -0.06), ["front"], (130, 10)), ("chin plate", (0.14, 0.0, -0.135), ["front"], (-170, 40)),
    ("hip opening", (0.05, 0.2, -0.07), ["side"], (-170, -10)),
    ("hip drum r54", (0.006, Y, -0.097), ["side"], (-190, 30)), ("thigh link 80 wide", (0.045, Y, -0.16), ["side"], (-200, 10)),
    ("thigh link", (0.05, Y + 0.04, -0.15), ["front"], (100, 0)),
    ("knee wheel (octagon, 74 across flats)", (0.071, Y, -0.233), ["side"], (-270, 0)), ("knee: barrel + 2 wheels, 102 wide", (0.07, Y + 0.05, -0.233), ["front"], (60, 0)),
    ("shin bar 77 wide", (0.02, Y, -0.31), ["side"], (-190, 10)), ("shin bar", (0.02, Y + 0.038, -0.31), ["front"], (100, 0)),
    ("ankle wheel", (-0.026, Y, -0.385), ["side"], (70, -10)), ("toe block", (0.09, Y, -0.45), ["side"], (-170, -40)),
    ("heel block", (-0.07, Y, -0.45), ["side"], (60, -30)), ("sole 272 x 128", (0.0, Y, -0.497), ["side"], (60, 25)),
    ("boot 131 wide", (0.1, Y + 0.065, -0.47), ["front"], (60, 0)),
]


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def draw_view(name):
    r, u, b = VIEWS[name]
    tex = Image.open(os.path.join(BP, f"oldtex_{name}.png")).convert("RGBA").resize((W * SC, W * SC), Image.LANCZOS)
    bg = Image.new("RGB", (W * SC, W * SC), (252, 252, 248))
    faded = Image.blend(Image.new("RGB", tex.size, (252, 252, 248)), tex.convert("RGB"), 0.5)
    bg.paste(faded, (0, 0), tex.split()[-1])
    d = ImageDraw.Draw(bg)
    buf = io.BytesIO()
    und = Image.new("RGBA", tex.size, (0, 0, 0, 0)); und.paste(faded, (0, 0), tex.split()[-1]); und.save(buf, "PNG")
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{W}" viewBox="0 0 {W} {W}" font-family="Arial" font-size="11">',
           f'<rect width="{W}" height="{W}" fill="#fcfcf8"/>',
           f'<image x="0" y="0" width="{W}" height="{W}" xlink:href="data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"/>']
    for k in range(-55, 56):
        x = W / 2 + k * 10
        strong = k % 10 == 0
        c = (120, 150, 190) if strong else (205, 215, 228)
        hexc = "#%02x%02x%02x" % c
        op = 0.9 if strong else 0.45
        svg.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{W}" stroke="{hexc}" stroke-width="{0.8 if strong else 0.4}" opacity="{op}"/>')
        svg.append(f'<line x1="0" y1="{x}" x2="{W}" y2="{x}" stroke="{hexc}" stroke-width="{0.8 if strong else 0.4}" opacity="{op}"/>')
        if strong:
            d.line([(x * SC, 0), (x * SC, W * SC)], fill=c, width=1); d.line([(0, x * SC), (W * SC, x * SC)], fill=c, width=1)
            svg.append(f'<text x="{x + 2}" y="{W - 4}" fill="#5078a0">{k} cm</text><text x="2" y="{x - 2}" fill="#5078a0">{-k} cm</text>')
            d.text(((x + 2) * SC, (W - 16) * SC), f"{k} cm", fill=(80, 120, 160), font=FONT); d.text((2 * SC, (x - 14) * SC), f"{-k} cm", fill=(80, 120, 160), font=FONT)
        elif k % 2 == 0:
            for q in range(0, W * SC, 6):
                d.point((x * SC, q), fill=c); d.point((q, x * SC), fill=c)
    for cls in ("core", "part", "vent", "leg", "seam", "light"):
        col = COL[cls]; hexc = "#%02x%02x%02x" % col
        path = []
        for c, x0, y0, x1, y1 in lines[name]:
            if c != cls:
                continue
            a = (W / 2 + x0 * 1000, W / 2 - y0 * 1000); e = (W / 2 + x1 * 1000, W / 2 - y1 * 1000)
            path.append("M%.2f %.2fL%.2f %.2f" % (a[0], a[1], e[0], e[1]))
            d.line([(a[0] * SC, a[1] * SC), (e[0] * SC, e[1] * SC)], fill=col, width=2 if cls != "core" else 1)
        svg.append(f'<path d="{"".join(path)}" fill="none" stroke="{hexc}" stroke-width="{0.9 if cls != "core" else 0.5}" stroke-linecap="round"/>')
    for text, pos, views, (dx, dy) in LABELS:
        if name not in views:
            continue
        x, y = W / 2 + dot(pos, r) * 1000, W / 2 - dot(pos, u) * 1000
        tx, ty = x + dx, y + dy
        tw = d.textlength(text, font=FONT) / SC
        ax = tx if dx >= 0 else tx + tw
        svg.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{ax:.1f}" y2="{ty - 4:.1f}" stroke="#222" stroke-width="0.6"/><circle cx="{x:.1f}" cy="{y:.1f}" r="1.6" fill="#222"/>')
        svg.append(f'<text x="{tx:.1f}" y="{ty:.1f}" fill="#000" stroke="#fcfcf8" stroke-width="3" paint-order="stroke">{text}</text>')
        d.line([(x * SC, y * SC), (ax * SC, (ty - 4) * SC)], fill=(40, 40, 40), width=1)
        d.ellipse([(x - 1.6) * SC, (y - 1.6) * SC, (x + 1.6) * SC, (y + 1.6) * SC], fill=(30, 30, 30))
        d.rectangle([(tx - 2) * SC, (ty - 11) * SC, (tx + tw + 2) * SC, (ty + 3) * SC], fill=(252, 252, 248))
        d.text((tx * SC, (ty - 11) * SC), text, fill=(0, 0, 0), font=FONT)
    notes = ["1 px = 1 mm in the SVG (PNG is 2 px per mm); grid 1 cm, strong lines every 10 cm; origin = rig origin.",
             "Underlay: the old model's own orthographic render (faded). Lines: planned parts, hidden lines removed.",
             "blue = shell panels and seams   black = parts   orange = lights   purple = vents   red = leg parts"]
    svg.append(f'<text x="12" y="22" font-size="15" font-weight="bold">{TITLE[name]}</text>')
    d.text((12 * SC, 8 * SC), TITLE[name], fill=(0, 0, 0), font=FONTB)
    for i, t in enumerate(notes):
        svg.append(f'<text x="12" y="{40 + i * 14}" fill="#333">{t}</text>')
        d.text((12 * SC, (30 + i * 14) * SC), t, fill=(50, 50, 50), font=FONT)
    svg.append("</svg>")
    open(os.path.join(BP, f"bp_{name}.svg"), "w", encoding="utf-8").write("\n".join(svg))
    bg.save(os.path.join(BP, f"bp_{name}.png"))
    return bg


ims = [draw_view(n) for n in ("front", "back", "side", "top")]
sheet = Image.new("RGB", (W * SC * 2, W * SC * 2), (255, 255, 255))
for i, im in enumerate(ims):
    sheet.paste(im, ((i % 2) * W * SC, (i // 2) * W * SC))
sheet.save(os.path.join(BP, "blueprint_sheet.png"))

# silhouette match per view + diff sheet (red = only old, cyan = only planned)
tiles = []
report = {}
for n in ("front", "back", "side", "top"):
    a = Image.open(os.path.join(BP, f"mask_old_{n}.png")).split()[-1]; bq = Image.open(os.path.join(BP, f"mask_new_{n}.png")).split()[-1]
    pa, pb = a.load(), bq.load()
    o = Image.new("RGB", a.size, (250, 250, 250)); po = o.load()
    both = oo = on = 0
    for y in range(a.size[1]):
        for x in range(a.size[0]):
            A, B = pa[x, y] > 127, pb[x, y] > 127
            if A and B:
                po[x, y] = (170, 170, 170); both += 1
            elif A:
                po[x, y] = (230, 40, 40); oo += 1
            elif B:
                po[x, y] = (30, 190, 220); on += 1
    report[n] = {"only_old_pct": round(100 * oo / (both + oo), 2), "only_new_pct": round(100 * on / (both + oo), 2), "iou_pct": round(100 * both / (both + oo + on), 2)}
    tiles.append(o)
sh = Image.new("RGB", (W * 2, W * 2), (255, 255, 255))
for i, t in enumerate(tiles):
    sh.paste(t, ((i % 2) * W, (i // 2) * W))
sh.save(os.path.join(BP, "silhouette_diff.png"))
json.dump(report, open(os.path.join(BP, "silhouette_score.json"), "w"), indent=1)
for k, v in report.items():
    print(k, v)
