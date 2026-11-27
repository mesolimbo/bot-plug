"""Draw the blueprint views (SVG + PNG) from bp_data.json, 1 px = 1 mm, old silhouette faint behind."""
import base64, io, json, os
from PIL import Image, ImageDraw, ImageFont

BP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "blueprints")
data = json.load(open(os.path.join(BP, "bp_data.json")))
VIEWS = {"front": ((0, 1, 0), (0, 0, 1), (1, 0, 0)), "back": ((0, -1, 0), (0, 0, 1), (-1, 0, 0)),
         "side": ((-1, 0, 0), (0, 0, 1), (0, 1, 0)), "top": ((0, -1, 0), (1, 0, 0), (0, 0, 1))}
TITLE = {"front": "FRONT (looking at the face; bot's left is on the right)", "back": "BACK (rear socket)",
         "side": "LEFT SIDE (front of bot to the left)", "top": "TOP (front of bot at the top)"}
COL = {"seam": (20, 90, 200), "opening": (0, 140, 120), "part": (30, 30, 30), "light": (230, 130, 0), "vent": (120, 60, 160), "leg": (150, 40, 40)}
W = 1100
SC = 2          # PNG supersample
try:
    FONT = ImageFont.truetype("arial.ttf", 11 * SC)
    FONTB = ImageFont.truetype("arialbd.ttf", 15 * SC)
except Exception:
    FONT = FONTB = ImageFont.load_default()


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def draw_view(name):
    r, u, b = VIEWS[name]
    P = lambda p: (W / 2 + dot(p, r) * 1000, W / 2 - dot(p, u) * 1000)
    sil = Image.open(os.path.join(BP, f"old_{name}.png")).convert("RGBA")
    a = sil.split()[-1].point(lambda v: 70 if v > 127 else 0)
    tint = Image.new("RGBA", sil.size, (255, 120, 120, 0)); tint.putalpha(a)
    buf = io.BytesIO(); tint.save(buf, "PNG")
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{W}" viewBox="0 0 {W} {W}" font-family="Arial" font-size="11">',
           f'<rect width="{W}" height="{W}" fill="#fbfbf7"/>']
    img = Image.new("RGB", (W * SC, W * SC), (251, 251, 247)); d = ImageDraw.Draw(img)
    # grid: 1 cm faint, 10 cm strong
    for k in range(-55, 56):
        x = W / 2 + k * 10
        strong = k % 10 == 0
        c = (150, 170, 200) if strong else (225, 230, 238)
        hexc = "#%02x%02x%02x" % c
        svg.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{W}" stroke="{hexc}" stroke-width="{1 if strong else 0.5}"/>')
        svg.append(f'<line x1="0" y1="{x}" x2="{W}" y2="{x}" stroke="{hexc}" stroke-width="{1 if strong else 0.5}"/>')
        d.line([(x * SC, 0), (x * SC, W * SC)], fill=c, width=2 if strong else 1); d.line([(0, x * SC), (W * SC, x * SC)], fill=c, width=2 if strong else 1)
        if strong:
            svg.append(f'<text x="{x + 2}" y="{W - 4}" fill="#6080a0">{k} cm</text><text x="2" y="{x - 2}" fill="#6080a0">{-k} cm</text>')
            d.text(((x + 2) * SC, (W - 16) * SC), f"{k} cm", fill=(96, 128, 160), font=FONT); d.text((2 * SC, (x - 14) * SC), f"{-k} cm", fill=(96, 128, 160), font=FONT)
    svg.append(f'<image x="0" y="0" width="{W}" height="{W}" xlink:href="data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"/>')
    img.paste(tint.resize((W * SC, W * SC)), (0, 0), tint.resize((W * SC, W * SC)))
    for it in data["items"]:
        pts, ns = it["pts"], it["n"]
        if it["cls"] == "leg" and name != "side":
            continue
        if it["cls"] == "legbox":
            if name == "side":
                continue
            q = [P(p) for p in pts]
            x0, x1, y0, y1 = min(a[0] for a in q), max(a[0] for a in q), min(a[1] for a in q), max(a[1] for a in q)
            dash = name == "top" and "boot" not in it["label"]
            svg.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="none" stroke="#962828" stroke-width="1.2"%s/>' % (x0, y0, x1 - x0, y1 - y0, ' stroke-dasharray="4 3"' if dash else ""))
            if not dash:
                d.rectangle([x0 * SC, y0 * SC, x1 * SC, y1 * SC], outline=(150, 40, 40), width=3)
            continue
        if it["closed"]:
            pts = pts + [pts[0]]; ns = ns + [ns[0]] if ns else None
        col = COL[it["cls"]]; hexc = "#%02x%02x%02x" % col
        run = []
        def flush():
            if len(run) > 1:
                svg.append('<polyline fill="none" stroke="%s" stroke-width="%.1f" points="%s"/>' % (hexc, 1.3 if it["cls"] != "vent" else 0.8, " ".join("%.1f,%.1f" % q for q in run)))
                d.line([(q[0] * SC, q[1] * SC) for q in run], fill=col, width=3 if it["cls"] != "vent" else 2)
            run.clear()
        for i, p in enumerate(pts):
            vis = True if ns is None else dot(ns[i], b) > 0.03
            if vis:
                run.append(P(p))
            else:
                flush()
        flush()
    for lb in data["labels"]:
        if name in lb["views"]:
            x, y = P(lb["pos"])
            svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2" fill="#000"/><text x="{x + 4:.1f}" y="{y - 3:.1f}" fill="#000" stroke="#fbfbf7" stroke-width="2.5" paint-order="stroke">{lb["text"]}</text>')
            d.ellipse([(x - 2) * SC, (y - 2) * SC, (x + 2) * SC, (y + 2) * SC], fill=(0, 0, 0))
            tw = d.textlength(lb["text"], font=FONT)
            d.rectangle([(x + 3) * SC, (y - 15) * SC, (x + 5) * SC + tw, (y - 2) * SC], fill=(251, 251, 247))
            d.text(((x + 4) * SC, (y - 15) * SC), lb["text"], fill=(0, 0, 0), font=FONT)
    notes = ["1 px = 1 mm; grid 1 cm (strong lines every 10 cm); origin = rig origin; pink = old model silhouette",
             "blue = panel seams (2.4 mm gaps)   teal = shell openings   black = parts   orange = lights   purple = vent ribs/louvres   red = leg parts",
             "body: 524 (x) x 550 (y), z -144..+357, antenna tip z +498; feet on z -500"]
    svg.append(f'<text x="12" y="22" font-size="15" font-weight="bold">{TITLE[name]}</text>')
    d.text((12 * SC, 8 * SC), TITLE[name], fill=(0, 0, 0), font=FONTB)
    for i, t in enumerate(notes):
        svg.append(f'<text x="12" y="{40 + i * 14}" fill="#333">{t}</text>')
        d.text((12 * SC, (30 + i * 14) * SC), t, fill=(50, 50, 50), font=FONT)
    svg.append("</svg>")
    open(os.path.join(BP, f"bp_{name}.svg"), "w", encoding="utf-8").write("\n".join(svg))
    img.save(os.path.join(BP, f"bp_{name}.png"))
    return img


ims = [draw_view(n) for n in ("front", "back", "side", "top")]
sheet = Image.new("RGB", (W * SC * 2, W * SC * 2), (255, 255, 255))
for i, im in enumerate(ims):
    sheet.paste(im, ((i % 2) * W * SC, (i // 2) * W * SC))
sheet.save(os.path.join(BP, "blueprint_sheet.png"))
print("drawn")
