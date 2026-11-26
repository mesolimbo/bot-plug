# ---- common helpers for the rebuild -------------------------------------------------------------
import numpy as np, time
T0 = time.time()
C = Vector((0, 0, 0.08))            # body centre used for the direction-space work
RN = 0.265                           # nominal shell radius (for converting mm to angles)
COLL = "botr"                        # the reduced build lives in its own collection; botn (bot_new, decals) is never touched
rig = bpy.data.objects["bot_rig"]
rig.data.pose_position = "REST"
bpy.context.view_layer.update()


def fresh_collection():
    for nm in (COLL,):
        c = bpy.data.collections.get(nm)
        if c:
            for o in list(c.objects):
                me = o.data
                bpy.data.objects.remove(o, do_unlink=True)
                if me and me.users == 0:
                    bpy.data.meshes.remove(me)
            bpy.data.collections.remove(c)
    c = bpy.data.collections.new(COLL)
    scene.collection.children.link(c)
    return c


def drop(*prefixes):
    c = bpy.data.collections.get(COLL)
    if not c:
        return
    for o in list(c.objects):
        if any(o.name == p or o.name.startswith(p + ".") or (p.endswith("*") and o.name.startswith(p[:-1])) for p in prefixes):
            me = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            if me and me.users == 0:
                bpy.data.meshes.remove(me)


def coll():
    return bpy.data.collections[COLL]


def srgb(rgb):
    return tuple((c / 255) ** 2.2 for c in rgb) + (1,)


def mat(name, rgb, rough=0.6, metal=0.0, emit=0.0):
    m = bpy.data.materials.get(name)
    if m:
        return m                         # reuse the scene materials untouched (the screen one is textured by b9_final)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = srgb(rgb)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Emission Color"].default_value = srgb(rgb) if emit else (0, 0, 0, 1)
    b.inputs["Emission Strength"].default_value = emit
    m.diffuse_color = srgb(rgb)
    return m


ORDER = ["paint", "dark", "steel", "screen", "light", "stripe", "rubber", "grey", "plastic", "glow"]


def materials():
    return {
        "paint": mat("botn_paint", (222, 210, 188), 0.5),
        "dark": mat("botn_dark", (38, 36, 38), 0.45, 0.4),
        "steel": mat("botn_steel", (150, 146, 142), 0.35, 0.85),
        "screen": mat("botn_screen", (14, 14, 16), 0.12),
        "light": mat("botn_light", (255, 135, 20), 0.3, 0.0, 1.2),
        "stripe": mat("botn_stripe", (232, 170, 16), 0.5),
        "rubber": mat("botn_rubber", (22, 22, 24), 0.8),
        "grey": mat("botn_grey", (84, 82, 84), 0.5, 0.2),
        "plastic": mat("botn_plastic", (58, 58, 62), 0.75),
        "glow": bpy.data.materials["bot_glow"],      # inside of the pin holes (made by g/h_glow.py)
    }


M = materials()


def new_obj(name, bm, bone, m="paint", smooth=True, sharp=32):
    """bm -> object in the collection. m: material key for all faces (None keeps per-face material_index)."""
    me = bpy.data.meshes.new(name)
    if m is not None:
        for f in bm.faces:
            f.material_index = ORDER.index(m)
    for f in bm.faces:
        f.smooth = smooth
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    for k in ORDER:
        me.materials.append(M[k])
    ob = bpy.data.objects.new(name, me)
    coll().objects.link(ob)
    ob["bone"] = bone
    if smooth and sharp:
        me.set_sharp_from_angle(angle=math.radians(sharp))
    return ob


def apply_mod(ob, name):
    with bpy.context.temp_override(window=win, area=area, region=region, object=ob, active_object=ob, selected_objects=[ob]):
        bpy.ops.object.modifier_apply(modifier=name)


def boolean(ob, cutter, op="DIFFERENCE", keep=False, solver="EXACT"):
    md = ob.modifiers.new("bool", "BOOLEAN")
    md.operation = op
    md.solver = solver
    md.object = cutter
    apply_mod(ob, md.name)
    if not keep:
        me = cutter.data
        bpy.data.objects.remove(cutter, do_unlink=True)
        bpy.data.meshes.remove(me)


def tmp_obj(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    coll().objects.link(ob)
    return ob


# ---- direction helpers ---------------------------------------------------------------------------
def D(lon, lat):
    lo, la = math.radians(lon), math.radians(lat)
    return Vector((math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la)))


def lonlat(d):
    d = d.normalized()
    return math.degrees(math.atan2(d.y, d.x)), math.degrees(math.asin(max(-1, min(1, d.z))))


def catmull(P, closed=False, step=0.012):
    """Catmull-Rom through unit vectors P, resampled about every `step` radians. Returns unit vectors."""
    n = len(P)
    out = []
    segs = n if closed else n - 1
    for i in range(segs):
        p0 = P[(i - 1) % n] if (closed or i > 0) else P[0] + (P[0] - P[1])
        p1, p2 = P[i], P[(i + 1) % n]
        p3 = P[(i + 2) % n] if (closed or i + 2 < n) else P[n - 1] + (P[n - 1] - P[n - 2])
        k = max(1, int(math.ceil((p2 - p1).length / step)))
        for j in range(k):
            t = j / k
            v = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)
            out.append(v.normalized())
    if not closed:
        out.append(P[-1].normalized())
    return out


def polyline(P, step=0.012, closed=False):
    out = []
    Q = P + [P[0]] if closed else P
    for a, b in zip(Q[:-1], Q[1:]):
        k = max(1, int(math.ceil((b - a).length / step)))
        for j in range(k):
            out.append(a.lerp(b, j / k).normalized())
    if not closed:
        out.append(P[-1].normalized())
    return out


def LL(pts):
    return [D(lo, la) for lo, la in pts]


def S(pts, step=0.012):
    return catmull(LL(pts), False, step)


def Lp(pts, step=0.012):
    return polyline(LL(pts), step)


def _arc_dev(p, a, b):
    """Distance (on the unit sphere) from p to the great arc a-b. Radial sag does not count: the cutters are radial."""
    ab = b - a
    t = (p - a).dot(ab) / max(ab.length_squared, 1e-18)
    if t <= 0:
        return (p - a).length
    if t >= 1:
        return (p - b).length
    n = a.cross(b)
    if n.length < 1e-12:
        return (p - a).length
    return abs(p.dot(n.normalized()))


def _dp(n, dev, tol, keep):
    """Douglas-Peucker over indices 0..n-1; dev(k, i, j) = deviation of sample k from the piece i-j."""
    keep = set(keep) | {0, n - 1}
    ks = sorted(keep)
    stack = list(zip(ks[:-1], ks[1:]))
    while stack:
        i, j = stack.pop()
        if j - i < 2:
            continue
        m, dm = max(((k, dev(k, i, j)) for k in range(i + 1, j)), key=lambda x: x[1])
        if dm > tol:
            keep.add(m)
            stack += [(i, m), (m, j)]
    return sorted(keep)


def simp(P, tol_mm=0.06, closed=False, maxseg=0.045, corner=12.0, forced=()):
    """Thin out a sampled direction path: drop samples that sit within tol_mm (sideways, on the shell) of the great arc
    between the samples kept. Corners (turn > `corner` degrees) keep themselves and both neighbours, so a groove's corner
    shape is exactly what the full sampling gives; path ends keep their neighbour too. No piece is longer than maxseg (rad).
    forced: sample indices that must stay."""
    n0 = len(P)
    if n0 < 4:
        return list(P)
    Q = list(P) + ([P[0]] if closed else [])
    n = len(Q)
    keep = {0, 1, n - 2, n - 1} | set(forced)
    for i in range(n):
        if not closed and (i == 0 or i == n - 1):
            continue
        a, b, c = (Q[(i - 1) % n0] if closed else Q[i - 1]), Q[i], (Q[(i + 1) % n0] if closed else Q[i + 1])
        u, v = b - a, c - b
        if u.length < 1e-9 or v.length < 1e-9 or math.degrees(u.angle(v)) > corner:
            keep |= {max(i - 1, 0), i, min(i + 1, n - 1)}
            if closed and i == 0:
                keep.add(n - 2)
    if closed:
        keep.add(max(range(n - 1), key=lambda k: (Q[k] - Q[0]).length))
    idx = _dp(n, lambda k, i, j: _arc_dev(Q[k], Q[i], Q[j]), tol_mm / 1000 / RN, keep)
    out = []
    for i, j in zip(idx[:-1], idx[1:]):
        out.append(i)
        k = int(math.ceil((Q[j] - Q[i]).length / maxseg))
        for m in range(1, k):
            q = int(round(i + (j - i) * m / k))
            if i < q < j and q != out[-1]:
                out.append(q)
    out.append(idx[-1])
    if closed:
        out = out[:-1]
    return [Q[i] for i in out]


def _seg_dev(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-18)))
    return (p - (a + ab * t)).length


def simp_rows(rows, tol=0.0001, closed=False):
    """Thin out the stations of a swept solid: a station goes when every one of its section points lies within tol (metres)
    of the straight sweep between the stations kept. Ends (and sharp bends, which deviate) always stay."""
    n0 = len(rows)
    if n0 < 3:
        return list(rows)
    Q = list(rows) + ([rows[0]] if closed else [])
    n = len(Q)
    m = len(Q[0])
    keep = {0, n - 1}
    if closed:
        keep.add(max(range(n - 1), key=lambda k: (Q[k][0] - Q[0][0]).length))
    idx = _dp(n, lambda k, i, j: max(_seg_dev(Q[k][s], Q[i][s], Q[j][s]) for s in range(m)), tol, keep)
    if closed:
        idx = idx[:-1]
    return [Q[i] for i in idx]


def refine(bm, pos, tol, rounds=8, longest=None):
    """Adaptive tessellation before a mesh on the unit sphere is displaced: split every edge whose midpoint would end up
    more than tol(e) metres from the straight edge. pos(co, e) is where a vertex at co goes; tol(e) is None to leave e alone.
    longest(e), if given, is the longest an edge may stay (unit-sphere length), whatever its error."""
    total = 0
    for _ in range(rounds):
        todo = []
        for e in bm.edges:
            tl = tol(e)
            if tl is None:
                continue
            a, b = e.verts
            mid = (a.co.normalized() + b.co.normalized()).normalized() * (0.5 * (a.co.length + b.co.length))
            if (longest and (a.co - b.co).length > longest(e)) or ((pos(a.co, e) + pos(b.co, e)) / 2 - pos(mid, e)).length > tl:
                todo.append((e, mid))
        if not todo:
            break
        touched = set()
        for e, mid in todo:
            touched.update(e.link_faces)
            ne, nv = bmesh.utils.edge_split(e, e.verts[0], 0.5)
            nv.co = mid
        bmesh.ops.triangulate(bm, faces=[f for f in touched if f.is_valid and len(f.verts) > 3], quad_method="BEAUTY", ngon_method="BEAUTY")
        total += len(todo)
    return total


def _tangent(dirs, i):
    """Bisector of the two pieces meeting at sample i (same as the centred difference when the samples are evenly spaced)."""
    n = len(dirs)
    t = Vector((0, 0, 0))
    if i > 0:
        t += (dirs[i] - dirs[i - 1]).normalized()
    if i < n - 1:
        t += (dirs[i + 1] - dirs[i]).normalized()
    return t.normalized()


def ribbon_cutter(dirs, hw, r0=0.5, r1=1.5, name="rib"):
    """Thin radial wall along a direction path; hw = half width as an angle (radians)."""
    bm = bmesh.new()
    st = []
    n = len(dirs)
    for i, d in enumerate(dirs):
        t = _tangent(dirs, i)
        s = d.cross(t).normalized()
        l, r = (d + s * hw).normalized(), (d - s * hw).normalized()
        st.append([bm.verts.new(l * r0), bm.verts.new(r * r0), bm.verts.new(r * r1), bm.verts.new(l * r1)])
    for a, b in zip(st[:-1], st[1:]):
        for k in range(4):
            bm.faces.new((a[k], a[(k + 1) % 4], b[(k + 1) % 4], b[k]))
    bm.faces.new(st[0][::-1])
    bm.faces.new(st[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return tmp_obj(name, bm)


def cone_cutter(dirs, r0=0.5, r1=1.5, name="cone"):
    """Radial prism over a closed loop of directions (star-shaped about its mean direction)."""
    bm = bmesh.new()
    c = Vector((0, 0, 0))
    for d in dirs:
        c += d
    c.normalize()
    a = [bm.verts.new(d * r0) for d in dirs]
    b = [bm.verts.new(d * r1) for d in dirs]
    ca, cb = bm.verts.new(c * r0), bm.verts.new(c * r1)
    n = len(dirs)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i]))
        bm.faces.new((ca, a[j], a[i]))
        bm.faces.new((cb, b[i], b[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return tmp_obj(name, bm)


# ---- old-mesh radius field (equirect) -------------------------------------------------------------
FW, FH = 800, 400
_r = np.load(SP + r"\n\sph_rad.npy")
R_OLD = _r.reshape(FH, 2, FW, 2).mean(axis=(1, 3)).astype(np.float64)


def _minmax(a, fn):
    out = a.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            sh = np.roll(a, dx, axis=1)
            if dy == -1:
                sh = np.vstack([sh[:1], sh[:-1]])
            elif dy == 1:
                sh = np.vstack([sh[1:], sh[-1:]])
            out = fn(out, sh)
    return out


def closing(a, k):
    b = a
    for _ in range(k):
        b = _minmax(b, np.maximum)
    for _ in range(k):
        b = _minmax(b, np.minimum)
    return b


LAT = np.radians(90 - (np.arange(FH) + 0.5) * 180 / FH)


def blur(a, sigma_deg):
    """Gaussian blur: fixed sigma in latitude, sigma/cos(lat) in longitude (wraps)."""
    s = sigma_deg / (180 / FH)
    k = int(3 * s) + 1
    w = np.exp(-0.5 * (np.arange(-k, k + 1) / s) ** 2)
    w /= w.sum()
    pad = np.vstack([a[k:0:-1], a, a[-2:-k - 2:-1]])
    out = np.zeros_like(a)
    for i, wi in enumerate(w):
        out += wi * pad[i:i + FH]
    sl = s / np.maximum(np.cos(LAT), 0.08)
    f = np.fft.rfftfreq(FW)
    gain = np.exp(-2 * (math.pi ** 2) * (sl[:, None] ** 2) * (f[None, :] ** 2))
    return np.fft.irfft(np.fft.rfft(out, axis=1) * gain, n=FW, axis=1)


def samp(F, d):
    """Bilinear sample of an equirect field along direction d."""
    lo, la = lonlat(d)
    x = (lo + 180) / 360 * FW - 0.5
    y = (90 - la) / 180 * FH - 0.5
    x0 = math.floor(x)
    y0 = min(max(math.floor(y), 0), FH - 2)
    fx = x - x0
    fy = min(max(y - y0, 0), 1)
    i0, i1 = x0 % FW, (x0 + 1) % FW
    return (F[y0, i0] * (1 - fx) + F[y0, i1] * fx) * (1 - fy) + (F[y0 + 1, i0] * (1 - fx) + F[y0 + 1, i1] * fx) * fy


def erode(mask, k):
    m = mask.astype(np.float64)
    for _ in range(k):
        m = _minmax(m, np.minimum)
    return m


def cube_sphere(n, r=1.0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=n - 1, use_grid_fill=True)
    q = math.pi / 4
    for v in bm.verts:
        c = v.co
        w = Vector([math.tan(a * q) if abs(abs(a) - 1) > 1e-6 else a for a in c])
        v.co = w.normalized() * r
    return bm


R_CLOSE = closing(R_OLD, 2)
print("common ok")
