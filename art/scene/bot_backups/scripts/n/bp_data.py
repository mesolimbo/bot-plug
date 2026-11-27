# Dump the planned part outlines as 3D polylines for the blueprint, and render the old bot's silhouettes.
import json, os
BP = SP + r"\blueprints"
os.makedirs(BP, exist_ok=True)
items, labels = [], []
C_ = Vector((0, 0, 0.08))


def add(label, cls, pts, normals=None, closed=False):
    items.append({"label": label, "cls": cls, "closed": closed, "pts": [[round(c, 5) for c in p] for p in pts],
                  "n": [[round(c, 3) for c in n] for n in normals] if normals else None})


def lab(text, pos, views):
    labels.append({"text": text, "pos": [round(c, 4) for c in pos], "views": views})


def shell_pts(dirs):
    return [C_ + d * samp(R_CLOSE, d) for d in dirs], [d.copy() for d in dirs]


for name, path in SEAMS.items():
    p, n = shell_pts(path); add(name, "seam", p, n)
for name, path in SLOTS.items():
    p, n = shell_pts(path); add(name, "light", p, n)
for name, loop in OPENINGS:
    p, n = shell_pts(loop); add(name, "opening", p, n, True)


def circle(c, r, axis, n=64, a0=0, a1=360, ry=None):
    pts = []
    ry = ry or r
    for k in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * k / n)
        u, v = r * math.cos(a), ry * math.sin(a)
        pts.append(Vector(c) + (Vector((0, u, v)) if axis == "X" else Vector((u, 0, v)) if axis == "Y" else Vector((u, v, 0))))
    return pts


def ngon(c, r, axis, n=8, rot=22.5):
    return circle(c, r, axis, n, rot, rot + 360)


UP, FR, BK = [(0, 0, 1)], [(1, 0, 0)], [(-1, 0, 0)]
def nn(v, k): return [v[0]] * k

# top assembly
DOME_C = (-0.02, 0.0)
for nm, r, z in (("dome", 0.089, 0.343), ("dark ring", 0.123, 0.322)):
    p = circle((DOME_C[0], DOME_C[1], z), r, "Z"); add(nm, "part", p, nn(UP, len(p)), True)
p = circle((-0.008, 0, 0.314), 0.139, "Z", ry=0.150); add("collar", "part", p, nn(UP, len(p)), True)
dome_prof = [(0.0, 0.357), (0.05, 0.3565), (0.07, 0.354), (0.082, 0.348), (0.089, 0.338), (0.089, 0.326), (0.123, 0.322), (0.139, 0.314)]
for sgn in (1, -1):
    add("dome profile", "part", [(DOME_C[0] + sgn * r, 0, z) for r, z in dome_prof])
    add("dome profile", "part", [(DOME_C[0], sgn * r, z) for r, z in dome_prof])
for nm, (x, y), r in (("lug", (0.024, 0.12), 0.019), ("lug", (-0.127, 0.103), 0.018)):
    p = circle((x, y, 0.325), r, "Z", 24); add(nm, "part", p, nn(UP, len(p)), True)
AX, AY = -0.072, -0.154
p = ngon((AX, AY, 0.30), 0.022, "Z", 6, 0); add("antenna base", "part", p, nn(UP, len(p)), True)
ant_prof = [(0.03, 0.285), (0.022, 0.30), (0.013, 0.32), (0.007, 0.37), (0.0055, 0.43), (0.0055, 0.492), (0.0, 0.498)]
for sgn in (1, -1):
    add("antenna", "part", [(AX + sgn * r, AY, z) for r, z in ant_prof])
    add("antenna", "part", [(AX, AY + sgn * r, z) for r, z in ant_prof])
# vents: louvres on the recessed band (sphere R 0.259) and ribs
RV = 0.259
def band(lon0, lon1, lat):
    ds = [D(lon0 + (lon1 - lon0) * k / 24, lat) for k in range(25)]
    return [C_ + d * RV for d in ds], ds
for k in range(7):
    lat = 42.0 + k * 2.4
    half = 24 + (lat - 40) * 0.62
    p, n = band(-half, half, lat); add("front louvre", "vent", p, n)
for k in range(6):
    lat = 43.3 + k * 2.3
    p, n = band(150.5, 211 + (lat - 42) * 1.1, lat); add("rear louvre", "vent", p, n)
for k in range(2):
    lat = 48.2 + k * 2.2
    p, n = band(78, 134, lat); add("side slot louvre", "vent", p, n)
def rib(y, x0, x1):
    ps = []
    for k in range(9):
        x = x0 + (x1 - x0) * k / 8
        ps.append(Vector((x, y, C_.z + math.sqrt(max((RV + 0.006) ** 2 - x * x - y * y, 0)))))
    return ps, [(q - C_).normalized() for q in ps]
for y in (-0.032, 0.031):
    p, n = rib(y, 0.132, 0.206); add("front rib", "vent", p, n)
for y in (-0.057, 0.0, 0.057):
    p, n = rib(y, -0.142, -0.192); add("rear rib", "vent", p, n)
# face
FZ = 0.073
for nm, r, x in (("bezel outer", 0.167, 0.232), ("bezel crest", 0.150, 0.2433), ("screen edge", 0.136, 0.2337)):
    p = circle((x, 0, FZ), r, "X", 96); add(nm, "part", p, nn(FR, len(p)), True)
scr = [(-0.0707 + math.sqrt(0.333 ** 2 - (0.136 * k / 12) ** 2), 0.136 * k / 12) for k in range(-12, 13)]
add("screen dome", "part", [(x, 0, FZ + r) for x, r in scr]); add("screen dome", "part", [(x, r, FZ) for x, r in scr])
bez = [(0.229, 0.136), (0.236, 0.139), (0.2415, 0.145), (0.2433, 0.150), (0.2415, 0.156), (0.236, 0.162), (0.229, 0.167)]
for sgn in (1, -1):
    add("bezel", "part", [(x + 0.05 * sgn * r, 0, FZ + sgn * r) for x, r in bez]); add("bezel", "part", [(x, sgn * r, FZ) for x, r in bez])
for sgn in (1, -1):
    a0, a1 = (-21, 3) if sgn > 0 else (177, 201)
    p = circle((0.2445, 0, FZ), 0.156, "X", 12, a0, a1) + circle((0.2445, 0, FZ), 0.139, "X", 12, a1, a0)
    add("amber pill", "light", p, nn(FR, len(p)), True)
p = circle((0.236, 0, FZ), 0.166, "X", 12, 256, 284) + circle((0.236, 0, FZ), 0.152, "X", 12, 284, 256)
add("amber bar", "light", p, nn(FR, len(p)), True)
# rear socket
plate = rrect_yz(-0.052, 0.052, -0.02, 0.106, 0.036, 0.008)
add("socket plate", "part", [(-0.257, y, z) for y, z in plate], nn(BK, len(plate)), True)
for nm, r in (("socket ring", 0.036), ("socket ring", 0.031)):
    p = circle((-0.252, 0, 0.03), r, "X", 48); add(nm, "light", p, nn(BK, len(p)), True)
for a in (90, 210, 330):
    p = circle((-0.245, 0.0145 * math.cos(math.radians(a)), 0.03 + 0.0145 * math.sin(math.radians(a))), 0.0045, "X", 12); add("pin", "light", p, nn(BK, len(p)), True)
led = [(-0.0155, 0.073), (0.0155, 0.073), (0.0155, 0.091), (-0.0155, 0.091)]
add("LED bar", "light", [(-0.258, y, z) for y, z in led], nn(BK, 4), True)
hinge = [(-0.034, -0.035), (0.034, -0.035), (0.034, -0.014), (-0.034, -0.014)]
add("hinge", "part", [(-0.236, y, z) for y, z in hinge], nn(BK, 4), True)
for r in (0.050, 0.041):
    p = circle((-0.2302, 0, -0.075), r, "X", 48); add("flap", "part", p, nn(BK, len(p)), True)
add("flap side", "part", [(-0.2302, 0, -0.025), (-0.2302, 0, -0.125), (-0.205, 0, -0.125), (-0.205, 0, -0.025)])
# legs
rigd = bpy.data.objects["bot_rig"].data
def prism(label, prof, y0, y1):
    a = [(x, y0, z) for x, z in prof]; b = [(x, y1, z) for x, z in prof]
    add(label, "leg", a, None, True); add(label, "leg", b, None, True)
    add(label, "legbox", a + b)
for side in ("L", "R"):
    Hh, K, A = [rigd.bones[f"{b}.{side}"].head_local.copy() for b in ("thigh", "shin", "foot")]
    y = Hh.y
    def bar(a, b, s0, s1, t0, t1, t0b=None, t1b=None):
        u = (b - a); u.y = 0; u.normalize(); n = Vector((-u.z, 0, u.x))
        t0b = t0 if t0b is None else t0b; t1b = t1 if t1b is None else t1b
        return [((a + u * s0 + n * t0).x, (a + u * s0 + n * t0).z), ((a + u * s0 + n * t1).x, (a + u * s0 + n * t1).z),
                ((a + u * s1 + n * t1b).x, (a + u * s1 + n * t1b).z), ((a + u * s1 + n * t0b).x, (a + u * s1 + n * t0b).z)]
    prism("thigh bar", bar(Hh, K, 0.02, 0.162, -0.052, 0.037, -0.036, 0.036), y - 0.040, y + 0.040)
    prism("shin bar", bar(K, A, 0.03, 0.147, -0.021, 0.037, -0.019, 0.046), y - 0.038, y + 0.038)
    for nm, c in (("hip wheel", Hh), ("knee wheel", K), ("ankle wheel", A)):
        oct_ = [(p.x, p.z) for p in ngon((c.x, 0, c.z), 0.064, "Y", 8)][:-1]
        if nm == "hip wheel":
            oct_ = [(p.x, p.z) for p in circle((c.x, 0, c.z), 0.059, "Y", 32)][:-1]
        prism(nm, oct_, y - 0.050, y + 0.050)
        hub = circle((c.x, y + (0.05 if side == "L" else -0.05), c.z), 0.04, "Y", 24); add(nm + " hub", "leg", hub, None, True)
    boot = [(-0.118, -0.5), (0.156, -0.5), (0.156, -0.455), (0.10, -0.418), (0.05, -0.392), (0.0, -0.408), (-0.012, -0.445), (-0.03, -0.44), (-0.045, -0.41), (-0.07, -0.41), (-0.10, -0.432), (-0.118, -0.455)]
    prism("boot", boot, y - 0.064, y + 0.064)
    if side == "L":
        lab("hip wheel r59", (Hh.x, y, Hh.z), ["side"]); lab("thigh bar 80w x 142", ((Hh.x + K.x) / 2, y, (Hh.z + K.z) / 2), ["side", "front"])
        lab("knee wheel (octagon r64)", (K.x, y, K.z), ["side"]); lab("shin bar 76w x 117", ((K.x + A.x) / 2, y, (K.z + A.z) / 2), ["side", "back"])
        lab("ankle wheel", (A.x, y, A.z), ["side"]); lab("boot 274 x 128 x 109h", (0.02, y, -0.47), ["side", "front", "top"])

lab("screen r136 (face texture)", (0.26, 0, 0.073), ["front"]); lab("bezel r139-167, tilted 3 deg", (0.25, 0.0, 0.225), ["front", "side"])
lab("amber pill", (0.24, 0.15, 0.05), ["front"]); lab("amber pill", (0.24, -0.15, 0.05), ["front"]); lab("amber bar", (0.23, 0, -0.085), ["front"])
lab("corner light", (0.2, 0.09, 0.235), ["front"]); lab("brow panel", (0.2, 0, 0.245), ["front"])
lab("front vent: 2 ribs + 7 louvres", (0.17, 0, 0.275), ["front", "top"]); lab("rear vent: 3 ribs + 6 louvres", (-0.165, 0, 0.27), ["back", "top"])
lab("side vent slot", (-0.04, 0.165, 0.29), ["top", "side"])
lab("dome r89", (-0.02, 0, 0.357), ["top", "front", "side"]); lab("dark toothed ring r123", (-0.02, -0.105, 0.322), ["top"]); lab("collar ring + 2 lugs", (0.06, 0.125, 0.314), ["top"])
lab("antenna to z 0.498", (AX, AY, 0.45), ["front", "back", "side", "top"])
lab("leaf panel", (0.12, 0.2, 0.235), ["side", "top"]); lab("shoulder panel", (-0.1, 0.2, 0.22), ["side", "top"]); lab("side panel", (0.02, 0.27, 0.06), ["side"])
lab("cheek panel", (-0.2, 0.13, 0.02), ["back", "side"]); lab("cheek panel", (-0.2, -0.13, 0.02), ["back"]); lab("yellow chevron panel", (-0.21, 0.09, 0.2), ["back"])
lab("rear collar panel", (-0.2, 0, 0.225), ["back"]); lab("dark lower panel", (-0.17, 0.07, -0.115), ["back"])
lab("socket housing 132 x 148", (-0.25, 0, 0.118), ["back"]); lab("socket ring r36 @ z 0.030", (-0.25, 0.04, 0.03), ["back"]); lab("LEDs", (-0.25, 0.02, 0.082), ["back"]); lab("flap r50", (-0.23, 0.05, -0.075), ["back", "side"])
lab("bib seam", (0.2, 0.13, -0.06), ["front"]); lab("hip opening", (0.0, 0.2, -0.1), ["side"]); lab("belt seam", (0.1, 0.22, 0.2), ["side"]); lab("chin plate", (0.14, 0, -0.14), ["front"])
json.dump({"items": items, "labels": labels}, open(BP + r"\bp_data.json", "w"))

# old silhouettes (1 px = 1 mm, 1100 px, centred on the origin)
VIEWS = {"front": ((0, 1, 0), (0, 0, 1), (1, 0, 0)), "back": ((0, -1, 0), (0, 0, 1), (-1, 0, 0)),
         "side": ((-1, 0, 0), (0, 0, 1), (0, 1, 0)), "top": ((0, -1, 0), (1, 0, 0), (0, 0, 1))}
bpy.data.objects["bot_rig"].data.pose_position = "REST"
hidden = {o.name: o.hide_render for o in bpy.data.objects}
only_render(["bot"])
setup_wb(1100, True, "SINGLE")
cam = get_cam()
cam.data.ortho_scale = 1.1
for name, (r, u, b) in VIEWS.items():
    R = Matrix((r, u, b)).transposed()
    cam.matrix_world = Matrix.Translation(Vector(b) * 3) @ R.to_4x4()
    scene.render.filepath = BP + "\\old_" + name + ".png"
    bpy.ops.render.render(write_still=True)
for o in bpy.data.objects:
    o.hide_render = hidden.get(o.name, o.hide_render)
print("bp data", len(items), "items")
