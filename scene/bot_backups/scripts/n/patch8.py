# Watertight pass: every part becomes a closed solid.
def patch(p, pairs):
    s = open(p, encoding="utf-8").read()
    for a, b in pairs:
        assert a in s, (p, a)
        s = s.replace(a, b)
    open(p, "w", encoding="utf-8").write(s)


# ---------------- shell: panels keep their undersides (closed solids), groove floors and window frame are solids
s = open("n/b1_shell.py", encoding="utf-8").read()
a = s.index("# groove floors: a round-bottomed dark channel")
b = s.index('print("shell verts"')
s = s[:a] + '''# groove floors: a round-bottomed dark channel swept along every seam, between the two edge walls (closed solid strips)
GW = HW * RN + 0.0004
NSEG = 6
runs = []
for name, path in SEAMS.items():
    cur = []
    n_ = len(path)
    stops = [(e_, SEAMS[b_]) for a_, e_, b_ in TEES if a_ == name]
    for i, d in enumerate(path):
        ok = True
        # at a T-junction the floor stops at the wall of the groove it runs into
        if any(((e_ == "end" and i > n_ - 8) or (e_ == "start" and i < 8)) and closest_on(Bp, d)[1] < HW * 1.15 for e_, Bp in stops):
            ok = False
        rs = []
        if ok:
            t = (path[min(i + 1, n_ - 1)] - path[max(i - 1, 0)]).normalized()
            sv = d.cross(t).normalized()
            for sgn in (-1, 1):
                q = (d + sv * sgn * 3.0 * HW).normalized()
                k = label_at(*lonlat(q))
                if k >= 0:
                    rs.append(samp(FIELD[k], q))
            ok = bool(rs)
        if not ok:
            if len(cur) > 1:
                runs.append(cur)
            cur = []
            continue
        r0 = min(rs)
        row = [C + d * (r0 - 0.0030 - GW * math.sin(math.pi * j / NSEG)) + sv * (-GW * math.cos(math.pi * j / NSEG)) for j in range(NSEG + 1)]
        row += [C + d * (r0 - 0.0062) + sv * GW, C + d * (r0 - 0.0062) - sv * GW]
        cur.append(row)
    if len(cur) > 1:
        runs.append(cur)
new_obj("seam_floors", join_bm([strip_solid(r_) for r_ in runs]), "body", "dark", True, 60)

# window frame: a dark skirt all round the top opening, from just under the panel lips down to the grille floor,
# so the grilles and the slot are closed in by a proper frame instead of a gap under the panel edges
cl = Vector((0, 0, 0))
for d in top_loop:
    cl += d
cl.normalize()
st = []
nt = len(top_loop)
for i, d in enumerate(top_loop):
    t = (top_loop[(i + 1) % nt] - top_loop[i - 1]).normalized()
    sv = d.cross(t).normalized()
    if sv.dot(d - cl) < 0:
        sv = -sv                                   # points away from the opening, towards the panels
    q = (d + sv * 4.0 * HW).normalized()
    k = label_at(*lonlat(q))
    rp = samp(FIELD[k], q) if k >= 0 else samp(F_GLOB, d)
    lo_, la_ = lonlat(d)
    rf = 0.25325 + 0.00575 * math.cos(math.radians(lo_)) - 0.0025
    w0, w1 = 0.0004, -0.0024                       # lateral: just under the panel edge to 2.4 mm into the opening
    st.append([C + d * (rp - 0.0014) + sv * w0, C + d * (rp - 0.0014) + sv * w1, C + d * rf + sv * w1, C + d * rf + sv * w0])
new_obj("vent_frame", strip_solid(st, closed=True), "body", "dark", True, 40)
''' + s[b:]
s = s.replace('''inner_faces = [f for f in bm.faces if all(v not in outer_v for v in f.verts)]
bmesh.ops.delete(bm, geom=inner_faces, context="FACES")
''', '''# the inner sphere faces stay: every panel is a closed solid (top, lip, walls, underside)
''')
assert "the inner sphere faces stay" in s
open("n/b1_shell.py", "w", encoding="utf-8").write(s)

# ---------------- core: closed ball with pits (the pit floors replace the old liner sphere)
patch("n/b2_core.py", [
    ('''low = [f for f in bm.faces if all(v.co.length < 0.7 for v in f.verts)]
bmesh.ops.delete(bm, geom=low, context="FACES")
''', ""),
    ('''bm = cube_sphere(10, R_LINER + 0.002)
xform(bm, Matrix.Translation(C))
new_obj("liner", bm, "body", "rubber", True, 0)
''', ""),
])

# ---------------- top
patch("n/b3_top.py", [
    ("(0.0875, -0.0010), (0.0890, -0.0040), (0.0890, -0.0200)], (0, 0, 0), \"Z\", 72)", "(0.0875, -0.0010), (0.0890, -0.0040), (0.0890, -0.0200), (0, -0.0200)], (0, 0, 0), \"Z\", 72)"),
    ("ring = lathe([(0.086, -0.0190), (0.126, -0.0190)], (0, 0, 0), \"Z\", 72)", "ring = lathe([(0.086, -0.0190), (0.126, -0.0190), (0.126, -0.0250), (0.086, -0.0250)], (0, 0, 0), \"Z\", 72, close=True)"),
    ("(1.0, -0.0340), (1.0, -0.0470)], (0, 0, 0), \"Z\", 96, rfun=col_fun)", "(1.0, -0.0340), (1.0, -0.0470), (0.1225, -0.0470)], (0, 0, 0), \"Z\", 96, rfun=col_fun, close=True)"),
    ("(0.0190, top - 0.0060), (0.0190, bot)], (lx, ly, 0), \"Z\", 24)", "(0.0190, top - 0.0060), (0.0190, bot), (0, bot)], (lx, ly, 0), \"Z\", 24)"),
    ("(0.0390, 0.2900), (0.0390, 0.2650)], (AX, AY, 0), \"Z\", 32)", "(0.0390, 0.2900), (0.0390, 0.2650), (0, 0.2650)], (AX, AY, 0), \"Z\", 32)"),
    ("(0.0185, 0.3165), (0.0185, 0.3070)], (AX, AY, 0), \"Z\", 6)", "(0.0185, 0.3165), (0.0185, 0.3070), (0, 0.3070)], (AX, AY, 0), \"Z\", 6)"),
    ("mast = lathe([(0.0125, 0.3180),", "mast = lathe([(0, 0.3180), (0.0125, 0.3180),"),
])

# ---------------- face
patch("n/b4_face.py", [
    ("bz = lathe(BEZ, (0, 0, FZ), \"X\", 96)", "bz = lathe(BEZ, (0, 0, FZ), \"X\", 96, close=True)"),
    ("scr = lathe(prof, (0, 0, FZ), \"X\", 64)", "scr = lathe(prof + [(0.1367, 0.2240), (0, 0.2240)], (0, 0, FZ), \"X\", 64)"),
])

# ---------------- socket
patch("n/b5_socket.py", [
    ("(0.0358, XR - 0.0022), (0.0368, XR - 0.0010), (0.0368, XR + 0.0040)], (0, 0, SOCK_Z), \"X\", 48)", "(0.0358, XR - 0.0022), (0.0368, XR - 0.0010), (0.0368, XR + 0.0040)], (0, 0, SOCK_Z), \"X\", 48, close=True)"),
    ("(0.0420, BOSS_X + 0.0015), (0.0420, -0.2280)], (0, 0, SOCK_Z), \"X\", 48)", "(0.0420, BOSS_X + 0.0015), (0.0420, -0.2280), (0.0328, -0.2280)], (0, 0, SOCK_Z), \"X\", 48, close=True)"),
    ('''cup = lathe([(0.0328, XR + 0.0030), (0.0328, FLOOR), (0, FLOOR)], (0, 0, SOCK_Z), "X", 48)
if sum(f.normal.x for f in cup.faces if abs(f.normal.x) > 0.9) > 0:
    bmesh.ops.reverse_faces(cup, faces=cup.faces)
''', '''cup = lathe([(0, FLOOR), (0.0328, FLOOR), (0.0328, XR + 0.0030), (0.0345, XR + 0.0030), (0.0345, FLOOR + 0.0040), (0, FLOOR + 0.0040)], (0, 0, SOCK_Z), "X", 48)
'''),
    ("(0.0395, LID_IN + 0.0016), (0.0395, LID_IN - 0.0002)], (0, 0, SOCK_Z), \"X\", 48)", "(0.0395, LID_IN + 0.0016), (0.0395, LID_IN - 0.0002)], (0, 0, SOCK_Z), \"X\", 48, close=True)"),
])

# ---------------- legs
patch("n/b6_legs.py", [
    ("drum = lathe([(0.030, -0.083), (0.030, -0.059),", "drum = lathe([(0, -0.083), (0.030, -0.083), (0.030, -0.059),"),
    ("(0.034, 0.0625), (0.032, 0.066)], (HC.x, y0, HC.z)", "(0.034, 0.0625), (0.032, 0.066), (0, 0.066)], (HC.x, y0, HC.z)"),
    ("(0.028, 0.071), (0.031, 0.068), (0.031, 0.060)], (HC.x, y0, HC.z)", "(0.028, 0.071), (0.031, 0.068), (0.031, 0.060), (0, 0.060)], (HC.x, y0, HC.z)"),
    ('''    capf = lathe([(0.0, -0.083), (0.030, -0.083)], (HC.x, y0, HC.z), "Y", 40, rfun=lambda a, r, h: (r, sg * h))
''', ""),
    ('set_mat(drum, "dark"); set_mat(capf, "dark"); set_mat(hub, "paint")', 'set_mat(drum, "dark"); set_mat(hub, "paint")'),
    ("join_bm([drum, capf, hub])", "join_bm([drum, hub])"),
    ("(0.0064, capw + 0.0022), (0.0064, capw - 0.002)], (c.x, y0, c.z)", "(0.0064, capw + 0.0022), (0.0064, capw - 0.002), (0, capw - 0.002)], (c.x, y0, c.z)"),
])
print("patched 8")
