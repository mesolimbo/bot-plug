# ---- body shell: panels cut in direction space, each snapped to the old surface -----------------------
fresh_collection()
HW = 0.0015 / RN                       # seam half width (angle)
T_PANEL = 0.006                        # panel rim depth
SIGMA = globals().get("SIGMA_OVERRIDE", 3.5)


def solve_dir(fix, a, b, sign):
    """Direction of the outermost old-surface point with two fixed coordinates.
    fix 'x': a=y, b=z known, scan x inward from sign*0.4; fix 'z': a=x, b=y known, scan z from C.z + sign*0.4."""
    def pt(t):
        return Vector((sign * t, a, b)) if fix == "x" else Vector((a, b, C.z + sign * t))
    def f(t):
        p = pt(t) - C
        return p.length - samp(R_CLOSE, p.normalized())
    t = 0.4
    while t > 0.0 and f(t - 0.002) > 0:
        t -= 0.002
    lo, hi = t - 0.002, t
    for _ in range(20):
        mid = 0.5 * (lo + hi)
        if f(mid) > 0:
            hi = mid
        else:
            lo = mid
    return (pt(hi) - C).normalized()


# -- openings (closed loops) --
FACE_Y, FACE_Z, FACE_R = 0.0, 0.073, 0.1675
face_loop = [solve_dir("x", FACE_R * math.cos(t), FACE_Z + FACE_R * math.sin(t), 1) for t in [2 * math.pi * k / 96 for k in range(96)]]

def mir(pts):
    return [(-lo, la) for lo, la in pts]


# Window sides are single smooth arcs; window bottoms and the rear window's slanted side are straight.
top_loop = (Lp([(-22, 39.6), (-12, 40), (0, 40), (12, 40), (22, 39.6), (26.5, 39)])[:-1]
            + S([(26.5, 39), (31, 43.5), (37, 47), (45, 50), (53, 51.2), (61, 50.3), (67, 48), (73, 45.2)])
            + S([(75.8, 44.8), (90, 46.5), (105, 47), (120, 47), (135, 47.3), (147, 47.3)])
            + Lp([(150.2, 41.4), (165, 41.4), (180, 41.4), (195, 41.4), (210.5, 41.4)])
            + Lp([(211.5, 42.6), (226, 55.5)])
            + S([(228, 56), (240, 56), (260, 56), (280, 55), (290, 53.6), (296, 52.4), (300, 51.5)])[1:]
            + S([(300, 51.5), (307, 51.2), (315, 50), (323, 47), (329, 43.5), (333.5, 39)])[1:]
            + Lp([(333.5, 39), (338, 39.6)])[1:-1])


def rrect_yz(y0, y1, z0, z1, rt, rb, n=8):
    pts = []
    for (cy, cz, r, a0) in ((y1 - rt, z1 - rt, rt, 0), (y0 + rt, z1 - rt, rt, 90), (y0 + rb, z0 + rb, rb, 180), (y1 - rb, z0 + rb, rb, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cy + r * math.cos(a), cz + r * math.sin(a)))
    return pts


HOUSE = dict(y0=-0.066, y1=0.066, z0=-0.024, z1=0.124, rt=0.05, rb=0.012)
house_pts = rrect_yz(**HOUSE)
house_loop = polyline([solve_dir("x", y, z, -1) for y, z in house_pts], closed=True)

WELL = [(41.2, -65), (50, -60), (60, -47.5), (65, -41.5), (71, -34.5), (77.5, -30.3), (86, -28), (95, -29.7), (100, -33.2), (105, -37.8), (109.5, -41.2),
        (120, -49.8), (130, -60), (136, -67), (141, -70), (120, -74.5), (90, -76.5), (60, -74), (38, -68)]
well_L = catmull(LL(WELL), True)
well_R = catmull(LL(mir(WELL))[::-1], True)
OPENINGS = [("face", face_loop), ("top", top_loop), ("house", house_loop), ("wellL", well_L), ("wellR", well_R)]

# -- seams (open paths) --
def xy_path(pts, sign=-1):
    return polyline([solve_dir("z", x, y, sign) for x, y in pts], 0.012)


def _seg_x(a0, a1, b0, b1):
    """Intersection of two short arcs on the unit sphere (planar approximation about a0). Returns the point or None."""
    e1 = (a1 - a0)
    e1 -= a0 * e1.dot(a0)
    if e1.length < 1e-12:
        return None
    e1.normalize()
    e2 = a0.cross(e1)

    def uv(p):
        return (p - a0).dot(e1), (p - a0).dot(e2)
    (x1, y1), (x2, y2), (x3, y3), (x4, y4) = uv(a0), uv(a1), uv(b0), uv(b1)
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(den) < 1e-18:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / den
    if -1e-9 <= t <= 1 + 1e-9 and -1e-9 <= u <= 1 + 1e-9:
        return a0.lerp(a1, t).normalized()
    return None


def closest_on(B, p):
    best, bd = None, 1e9
    for b0, b1 in zip(B[:-1], B[1:]):
        d = b1 - b0
        t = max(0, min(1, (p - b0).dot(d) / max(d.length_squared, 1e-18)))
        q = b0 + d * t
        if (q - p).length < bd:
            bd, best = (q - p).length, q.normalized()
    return best, bd


def trim_to(A, B, end=True):
    """Make path A stop exactly on the centre line of path B (a T-junction): cut it where it crosses, or extend it to reach."""
    P = A if end else A[::-1]
    for i in range(len(P) - 1, max(0, len(P) - 30), -1):
        for b0, b1 in zip(B[:-1], B[1:]):
            if (b0 - P[i]).length > 0.05:
                continue
            X = _seg_x(P[i - 1], P[i], b0, b1)
            if X is not None:
                out = P[:i] + [X]
                if (out[-1] - out[-2]).length < 0.003 and len(out) > 2:
                    out = out[:-2] + [X]
                return out if end else out[::-1]
    q, _ = closest_on(B, P[-1])
    out = P + [q]
    return out if end else out[::-1]


def fork_cutter(A, B, name, sep_mm=2.5):
    """Where path A (starting on B) leaves B at a shallow angle, remove the knife-edge sliver between the two grooves
    so they blend into one: a thin triangle from the fork point out to where the panel between them is sep_mm wide."""
    Pf = A[0]
    need = 2 * HW + sep_mm / 1000 / RN
    j = min(range(len(B)), key=lambda k: (B[k] - Pf).length)
    best = None
    for dirn in (1, -1):
        Bs = B[j::dirn]
        if len(Bs) < 3 or len(A) < 3:
            continue
        dd = (Bs[min(4, len(Bs) - 1)] - A[min(4, len(A) - 1)]).length
        if best is None or dd < best[0]:
            best = (dd, Bs)
    Bs = best[1]
    la, lb = [Pf], [Pf]
    for k in range(1, min(len(A), len(Bs), 60)):
        la.append(A[k])
        lb.append(closest_on(Bs, A[k])[0])
        if (la[-1] - lb[-1]).length >= need:
            break
    loop = la + lb[:0:-1]
    c = Vector((0, 0, 0))
    for d in loop:
        c += d
    c.normalize()
    e1 = c.orthogonal().normalized()
    e2 = c.cross(e1)
    n = len(loop)
    area = sum(loop[i].dot(e1) * loop[(i + 1) % n].dot(e2) - loop[(i + 1) % n].dot(e1) * loop[i].dot(e2) for i in range(n))
    if area < 0:
        loop = loop[::-1]
    return cone_cutter(loop, name="cut_" + name)


# Clean, single-curvature curves fitted through the old (wobbly) painted lines; mirrored where the design is symmetric.
BELT_TOP = [(24.3, 35.3), (50, 34.4), (75, 31), (95, 26.2), (107, 22.3), (114.5, 21.0), (123, 22.6), (132, 25.6), (140.5, 27.5), (150, 27.6), (160, 25.6), (170, 20.9), (176, 16.6), (180, 13.4)]
SIDE = [(113.6, 21.2), (116.4, 17.6), (119.3, 11), (121, 0), (121, -12), (119.8, -21), (116.3, -29), (111.7, -35.5), (107, -42)]
UPPER_L = [(72.5, 47.5), (76, 42), (83, 38), (92, 34.5), (101, 30), (108.5, 25.6)]
STRIPE_TOP = [(119.2, 30.2), (130, 32.6), (140, 34.4), (152, 35.2), (160, 33.5), (168, 30.4), (174.5, 26.7), (180, 22.7)]
STRIPE_END = [(123.9, 21.9), (119.2, 30.2)]
CHEEK_LOW = [(120.2, -10.5), (121.6, -14.5), (123.5, -21), (127, -29), (131, -36), (136, -41.5), (140, -45), (145, -48), (152.5, -52), (160, -54), (170, -54.4), (180, -54.4)]
FLARE = [(139.6, -46.4), (141.5, -44.8), (149, -42.3), (156.5, -36), (161, -29.5), (164.0, -24.2), (165.6, -21.2)]
BIB = [(55.4, -10.6), (53.8, -17.5), (51, -24.5), (46.5, -33), (41.3, -42), (35, -51), (28.5, -59), (22, -65.3), (14.6, -70.3), (7, -70.9), (0, -71.0)]
WIN = [(149.7, 42.4), (149.5, 34.0)]
BELLY = [(-0.142, 0.041), (-0.058, 0.014), (0.0, 0.030), (0.073, 0.019), (0.105, 0.034), (0.166, 0.041)]
SEAMS = {
    "belt": S(BELT_TOP) + S(mir(BELT_TOP))[::-1][1:],
    "upperSideL": S(UPPER_L + SIDE), "sideR": S(mir(SIDE)),
    "arcR": S([(-57.5, 54.8), (-62, 52), (-66.5, 50.4), (-72, 48.8), (-82, 45), (-92, 43), (-101, 43), (-108, 44.5), (-113, 48), (-117, 53), (-119, 57.5)]),
    "vtip": Lp([(180, 13.4), (180, 8.5)]),
    "stripe": Lp(STRIPE_END)[:-1] + S(STRIPE_TOP) + S(mir(STRIPE_TOP))[::-1][1:] + Lp(mir(STRIPE_END)[::-1])[1:],
    "winL": Lp(WIN), "winR": Lp(mir(WIN)),
    "cheekLow": S(CHEEK_LOW + [(360 - lo, la) for lo, la in CHEEK_LOW[-2::-1]]),
    "flareL": S(FLARE), "flareR": S(mir(FLARE)),
    "bib": S(BIB + mir(BIB[-2::-1])),
    "belly": xy_path([(x, -y) for x, y in BELLY] + BELLY[::-1]),
    "trapFront": xy_path([(-0.058, -0.016), (-0.058, 0.016)]),
}
# T-junctions: (seam, which end, the seam it stops on). The first seam ends exactly on the centre line of the second.
TEES = [("sideR", "start", "belt"), ("stripe", "start", "belt"), ("stripe", "end", "belt"), ("winL", "end", "stripe"), ("winR", "end", "stripe"),
        ("cheekLow", "start", "upperSideL"), ("cheekLow", "end", "sideR"), ("flareL", "start", "cheekLow"), ("flareR", "start", "cheekLow"),
        ("belly", "start", "cheekLow"), ("belly", "end", "cheekLow"), ("trapFront", "start", "belly"), ("trapFront", "end", "belly")]
for a_, e_, b_ in TEES:
    SEAMS[a_] = trim_to(SEAMS[a_], SEAMS[b_], e_ == "end")
# shallow forks to blend: (seam leaving, reversed?, seam it leaves)
FORKS = [("cheekLow", False, "upperSideL"), ("cheekLow", True, "sideR")]
JUNCTION_PTS = {f"{a_}.{e_} on {b_}": (SEAMS[a_][-1] if e_ == "end" else SEAMS[a_][0]) for a_, e_, b_ in TEES}
JUNCTION_PTS["X upperSideL x belt"] = D(113.6, 21.2)
JUNCTION_PTS["V belt + vtip"] = D(180, 13.4)
JUNCTION_PTS["V stripe"] = D(180, 22.7)
JUNCTION_PTS["stripe corner L"] = D(119.2, 30.2)
JUNCTION_PTS["stripe corner R"] = D(-119.2, 30.2)
JUNCTION_PTS["bib x belly L"] = D(14.6, -70.3)
JUNCTION_PTS["bib x belly R"] = D(-14.6, -70.3)
JUNCTION_PTS["bib end L"] = D(55.4, -10.6)
JUNCTION_PTS["arcR start"] = D(-62, 52)
JUNCTION_PTS["upperSideL start"] = D(74, 45)
JUNCTION_PTS["belt start L"] = D(24.3, 35.3)
SLOTS = {"slotL": Lp([(27.6, 40.6), (19.3, 29.0)]), "slotR": Lp([(-27.6, 40.6), (-19.3, 29.0)])}
SLOT_HW = 0.0042 / RN
# Reduced build: the cutters follow thinned paths (see simp). The full sampling stays for the fork cutters, the groove
# floors and the window frame, which are thinned afterwards as swept solids.
SEAM_TOL = 0.06      # mm, sideways
SEAMS_FULL = dict(SEAMS)
# Where two cuts run close together (junctions, forks, a seam ending on an opening) every sample stays: the thin slivers left
# between them are cleaned up further down by merging close vertices, and that only works as before with the full sampling.
PROX = 0.006 / RN
_paths = dict(SEAMS)
_paths.update({"o_" + n_: l_ for n_, l_ in OPENINGS})
_paths.update(SLOTS)
_arr = {k_: np.array([tuple(p_) for p_ in v_]) for k_, v_ in _paths.items()}


def _crowded(name):
    A = _arr[name]
    near = np.zeros(len(A), bool)
    for k_, B in _arr.items():
        if k_ != name:
            near |= (np.linalg.norm(A[:, None, :] - B[None, :, :], axis=2) < PROX).any(axis=1)
    return [int(i) for i in np.nonzero(near)[0]]


SEAMS = {k_: simp(v_, SEAM_TOL, forced=_crowded(k_)) for k_, v_ in SEAMS.items()}
OPENINGS = [(n_, l_ if n_ == "face" else simp(l_, SEAM_TOL, closed=True, forced=_crowded("o_" + n_))) for n_, l_ in OPENINGS]
print("seam samples", sum(len(v_) for v_ in SEAMS_FULL.values()), "->", sum(len(v_) for v_ in SEAMS.values()),
      "| opening samples", len(top_loop) + len(house_loop) + 2 * len(well_L), "->", sum(len(l_) for n_, l_ in OPENINGS if n_ != "face"))
SLOTS = {k_: simp(v_, SEAM_TOL, forced=_crowded(k_)) for k_, v_ in SLOTS.items()}

# -- the solid shell on the unit sphere, cut --
NS = 32        # was 64: the panels are smooth (field blurred over 3.5 degrees), so 2.8 degree cells hold them
NS_IN = 10                                # was 32: the panel undersides are never seen
bm = cube_sphere(NS, 1.0)
inner = cube_sphere(NS_IN, 0.97)
bmesh.ops.reverse_faces(inner, faces=inner.faces)
me_in = bpy.data.meshes.new("tmp_in"); inner.to_mesh(me_in); inner.free()
bm.from_mesh(me_in); bpy.data.meshes.remove(me_in)
# the bigger cells are too far from flat for the exact boolean (it dropped or fused whole panels): cut triangles instead
bmesh.ops.triangulate(bm, faces=bm.faces, quad_method="SHORT_EDGE")
shell = tmp_obj("shell_unit", bm)
t = time.time()
for name, loop in OPENINGS:
    boolean(shell, cone_cutter(loop, name="cut_" + name))
for name, path in SLOTS.items():
    boolean(shell, ribbon_cutter(path, SLOT_HW, name="cut_" + name))
for name, path in SEAMS.items():
    boolean(shell, ribbon_cutter(path, HW, name="cut_" + name))
for a_, rev_, b_ in FORKS:
    boolean(shell, fork_cutter(SEAMS_FULL[a_][::-1] if rev_ else SEAMS_FULL[a_], SEAMS_FULL[b_], "fork_" + a_))
print("cuts done %.1fs, verts %d" % (time.time() - t, len(shell.data.vertices)))

# -- islands --
bm = bmesh.new(); bm.from_mesh(shell.data)
def _probe(tag):
    bv = BVHTree.FromBMesh(bm)
    h = bv.ray_cast(D(0, 37) * 1.2, -D(0, 37))
    h2 = bv.ray_cast(D(0, 37) * 0.98, D(0, 37))
    print("stage", tag, "inward hit r", round(h[0].length, 3) if h[0] else None, "outward hit r", round(h2[0].length, 3) if h2[0] else None)
_probe("A")
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
_probe("B")
outer_v = {v for v in bm.verts if v.co.length > 0.985}
# the inner sphere faces stay: every panel is a closed solid (top, lip, walls, underside)
_probe("C")
outer_v = {v for v in bm.verts if v.co.length > 0.985}
# triangulate n-gons on the outer surface so they stay well-shaded after displacement
ng = [f for f in bm.faces if len(f.verts) > 4]
bmesh.ops.triangulate(bm, faces=ng, quad_method="BEAUTY", ngon_method="BEAUTY")
panel_layer = bm.faces.layers.int.new("panel")
outer_layer = bm.verts.layers.int.new("outer")
bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
bm.verts.index_update(); bm.faces.index_update()
outer_v = {v for v in bm.verts if v.co.length > 0.985}
for v in outer_v:
    v[outer_layer] = 1
isl = {}
islands = []
for f in bm.faces:
    if f in isl:
        continue
    k = len(islands); stack = [f]; isl[f] = k; faces = []
    while stack:
        g = stack.pop(); faces.append(g)
        for e in g.edges:
            for h in e.link_faces:
                if h not in isl:
                    isl[h] = k; stack.append(h)
    islands.append(faces)
_bv = BVHTree.FromBMesh(bm)
for _lo, _la in ((0, 37), (10, 37), (50, 42), (140, 0)):
    _h = _bv.ray_cast(D(_lo, _la) * 1.2, -D(_lo, _la))
    if _h[0] is not None:
        _f = bm.faces[_h[2]]
        print("probe", _lo, _la, "island", isl.get(_f), "n faces", len(islands[isl[_f]]), "hit r %.3f" % _h[0].length, "outer", all(v in outer_v for v in _f.verts))
    else:
        print("probe", _lo, _la, "MISS")
def outer_area(faces):
    return sum(f.calc_area() for f in faces if all(v in outer_v for v in f.verts))
areas = [outer_area(fs) for fs in islands]
small = [k for k, a in enumerate(areas) if a < 2.5e-4]
print("islands", len(islands), "small dropped", len(small), "areas(cm2 at r=.265)", sorted(round(a * RN * RN * 1e4, 1) for a in areas))
assert len(islands) == 14 and not small, "a panel went missing in the cuts"
kill = [f for k in small for f in islands[k]]
keep_ids = [k for k in range(len(islands)) if k not in small]

# -- label map (which island each direction belongs to) --
bm.verts.index_update()
verts = [v.co.copy() for v in bm.verts]
polys, pid = [], []
for k in keep_ids:
    for f in islands[k]:
        if all(v in outer_v for v in f.verts):
            polys.append([v.index for v in f.verts]); pid.append(k)
lab_bvh = BVHTree.FromPolygons(verts, polys)
LABEL = np.full((FH, FW), -1, np.int32)
for j in range(FH):
    la = 90 - (j + 0.5) * 180 / FH
    for i in range(FW):
        lo = -180 + (i + 0.5) * 360 / FW
        h = lab_bvh.ray_cast(Vector((0, 0, 0)), D(lo, la))
        if h[0] is not None:
            LABEL[j, i] = pid[h[2]]

def label_at(lon, lat):
    h = lab_bvh.ray_cast(Vector((0, 0, 0)), D(lon, lat))
    return pid[h[2]] if h[0] is not None else -1

# The fields are sensitive to single label pixels along panel edges, so they are built from the label map of the full-resolution
# build (label_full.npy, saved by running n/b1_shell.py): the panel surfaces then match the full model exactly.
_L0 = np.load(SP + r"\n_low\label_full.npy")
_LN = LABEL
LABEL = np.full_like(_L0, -1)
for k0 in np.unique(_L0[_L0 >= 0]):
    hit = _LN[(_L0 == k0) & (_LN >= 0)]
    LABEL[_L0 == k0] = np.bincount(hit).argmax()
assert sorted(np.unique(LABEL[LABEL >= 0])) == sorted(keep_ids), "label maps do not correspond"
print("label pixels that differ from this build's own map:", int((LABEL != _LN).sum()))

# -- fields --
any_w = (LABEL >= 0).astype(np.float64)
F_GLOB = blur(R_CLOSE * any_w, 6) / np.maximum(blur(any_w, 6), 1e-6)
FIELD = {}
for k in keep_ids:
    w = erode(LABEL == k, 2)
    if w.sum() < 4:
        w = (LABEL == k).astype(np.float64)
    for it in range(3):
        den = blur(w, SIGMA)
        F = blur(R_CLOSE * w, SIGMA) / np.maximum(den, 1e-9)
        res = np.abs(R_CLOSE - F)
        w = erode(LABEL == k, 2) * (res < (0.006 if it == 0 else 0.004))
    FIELD[k] = np.where(den > 1e-4, F, F_GLOB)
# lowest panel surface around each direction: the dark core sits below this, so it never shows through a recessed panel
F_LAB = F_GLOB.copy()
for k in keep_ids:
    F_LAB = np.where(LABEL == k, FIELD[k], F_LAB)
F_LOW = F_LAB
for _ in range(7):
    F_LOW = _minmax(F_LOW, np.minimum)
F_LOW = np.minimum(blur(F_LOW, 1.2), F_GLOB)
print("fields %.1fs" % (time.time() - T0))

# -- displace --
bmesh.ops.delete(bm, geom=kill, context="FACES")
loose = [v for v in bm.verts if not v.link_faces]
bmesh.ops.delete(bm, geom=loose, context="VERTS")
# refine: the cells are twice the size they were, so split edges wherever the straight edge would leave the panel surface
# by more than 0.15 mm (undersides: 1.5 mm). Flat stretches keep the big cells; tight curvature gets the old density back.
for f in bm.faces:
    f[panel_layer] = isl[f]


def _shell_pos(co, e):
    d = co.normalized()
    r = samp(FIELD[e.link_faces[0][panel_layer]], d)
    return d * (r if co.length > 0.985 else r - T_PANEL)


def _shell_tol(e):
    oa, ob = e.verts[0].co.length > 0.985, e.verts[1].co.length > 0.985
    return None if oa != ob else (TOL_OUT if oa else 0.0015)


TOL_OUT = 0.00015
print("refine: edges split", refine(bm, _shell_pos, _shell_tol), "faces", len(bm.faces))
isl = {f: f[panel_layer] for f in bm.faces}
outer_v = {v for v in bm.verts if v.co.length > 0.985}
for v in outer_v:
    v[outer_layer] = 1
vk = {}
for f in bm.faces:
    k = isl.get(f)
    for v in f.verts:
        vk[v] = k
for v in bm.verts:
    d = v.co.normalized()
    r = samp(FIELD[vk[v]], d)
    v.co = C + d * (r if v.co.length > 0.985 else r - T_PANEL)

# -- materials per island --
PROBES = {"grey": [(180, -45)], "stripe": [(150, 31.5)]}
mat_of = {}
for key, pts in PROBES.items():
    for lo, la in pts:
        mat_of[label_at(lo, la)] = key
for f in bm.faces:
    f.material_index = ORDER.index(mat_of.get(isl.get(f), "paint"))
wall = ORDER.index("dark")
for f in bm.faces:
    f[panel_layer] = isl.get(f, -1)
    if any(v not in outer_v for v in f.verts):
        f.material_index = wall          # electrocoated seam bands: the panel edge walls are dark
me = shell.data
bpy.data.objects.remove(shell, do_unlink=True); bpy.data.meshes.remove(me)
# crisp lip: a small hard chamfer where each panel top turns into its edge wall
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0007)     # merge the tiny edges the cuts leave, so the chamfer stays even
outer_v = {v for v in bm.verts if v[outer_layer]}
rim = [e for e in bm.edges if len(e.link_faces) == 2 and (all(v in outer_v for v in e.link_faces[0].verts) != all(v in outer_v for v in e.link_faces[1].verts))]
res = bmesh.ops.bevel(bm, geom=rim, offset=0.00045, segments=1, affect="EDGES", profile=0.5, clamp_overlap=True)
newf = set(res["faces"])
for f in newf:
    for e in f.edges:
        for g in e.link_faces:
            if g not in newf and g.material_index != wall:
                f.material_index = g.material_index
                f[panel_layer] = g[panel_layer]
shell = new_obj("shell", bm, "body", m=None, smooth=True, sharp=40)

# groove floors: a round-bottomed dark channel swept along every seam, between the two edge walls (closed solid strips)
GW = HW * RN + 0.0004
NSEG = 3                                  # was 6 (plus a flat two-point underside, now one point): 5 section points instead of 9
runs = []
for name, path in SEAMS_FULL.items():
    cur = []
    n_ = len(path)
    stops = [(e_, SEAMS_FULL[b_]) for a_, e_, b_ in TEES if a_ == name]
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
        row += [C + d * (r0 - 0.0062)]
        cur.append(row)
    if len(cur) > 1:
        runs.append(cur)
_n0 = sum(len(r_) for r_ in runs)
runs = [simp_rows(r_, 0.0001) for r_ in runs]
print("floor stations", _n0, "->", sum(len(r_) for r_ in runs))
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
_n0 = len(st)
st = simp_rows(st, 0.00006, closed=True)
print("frame stations", _n0, "->", len(st))
new_obj("vent_frame", strip_solid(st, closed=True), "body", "dark", True, 40)
print("shell verts", len(shell.data.vertices), "faces", len(shell.data.polygons), "t %.1f" % (time.time() - T0))

# -- distance stats of the outer shell verts to the old body surface --
np.save(SP + r"\n_low\label.npy", LABEL)
