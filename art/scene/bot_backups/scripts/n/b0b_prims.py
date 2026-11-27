# ---- primitive builders ---------------------------------------------------------------------------
AXF = {"Z": (Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))),
       "X": (Vector((0, 1, 0)), Vector((0, 0, 1)), Vector((1, 0, 0))),
       "Y": (Vector((0, 0, 1)), Vector((1, 0, 0)), Vector((0, 1, 0)))}


def lathe(prof, origin, axis="Z", segs=64, rfun=None, close=False):
    """Spin prof [(r, h)] about `axis` through origin. r == 0 ends are capped with fans.
    rfun(angle, r, h) -> (r, h) lets the section vary with angle. close=True joins last to first profile point."""
    e1, e2, ax = AXF[axis]
    origin = Vector(origin)
    bm = bmesh.new()
    rings = []
    for k in range(segs):
        a = 2 * math.pi * k / segs
        ring = []
        for r, h in prof:
            if rfun:
                r, h = rfun(a, r, h)
            ring.append(bm.verts.new(origin + e1 * (r * math.cos(a)) + e2 * (r * math.sin(a)) + ax * h))
        rings.append(ring)
    n = len(prof)
    pairs = [(i, i + 1) for i in range(n - 1)] + ([(n - 1, 0)] if close else [])
    for k in range(segs):
        A, B = rings[k], rings[(k + 1) % segs]
        for i, j in pairs:
            z0, z1 = prof[i][0] == 0, prof[j][0] == 0
            if z0 and z1:
                continue
            vs = [A[i], B[i], B[j], A[j]]
            if z0:
                vs = [A[i], B[j], A[j]]
            elif z1:
                vs = [A[i], B[i], A[j]]
            bm.faces.new(vs)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def strip_solid(stations, closed=False, caps=True):
    """Solid from a list of cross-sections (each a list of Vectors, same count, same winding)."""
    bm = bmesh.new()
    S_ = [[bm.verts.new(p) for p in st] for st in stations]
    m = len(S_[0])
    pairs = list(zip(S_[:-1], S_[1:])) + ([(S_[-1], S_[0])] if closed else [])
    for a, b in pairs:
        for k in range(m):
            bm.faces.new((a[k], a[(k + 1) % m], b[(k + 1) % m], b[k]))
    if caps and not closed:
        bm.faces.new(S_[0][::-1])
        bm.faces.new(S_[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def arc_solid(sect, origin, axis, a0, a1, segs=12, rfun=None):
    """Sweep a closed section [(r, h)] through angles a0..a1 (degrees) about axis; capped ends."""
    e1, e2, ax = AXF[axis]
    origin = Vector(origin)
    st = []
    for k in range(segs + 1):
        a = math.radians(a0 + (a1 - a0) * k / segs)
        row = []
        for r, h in sect:
            if rfun:
                r, h = rfun(a, r, h)
            row.append(origin + e1 * (r * math.cos(a)) + e2 * (r * math.sin(a)) + ax * h)
        st.append(row)
    return strip_solid(st)


def prism(poly, p0, p1):
    """Extrude a polygon of 3D offsets: poly is a list of Vectors (a closed planar section), swept from p0 to p1."""
    return strip_solid([[Vector(p0) + q for q in poly], [Vector(p1) + q for q in poly]])


def box_bm(x0, x1, y0, y1, z0, z1):
    x0, x1 = min(x0, x1), max(x0, x1)
    y0, y1 = min(y0, y1), max(y0, y1)
    z0, z1 = min(z0, z1), max(z0, z1)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector(((x0 + x1) / 2 + v.co.x * (x1 - x0), (y0 + y1) / 2 + v.co.y * (y1 - y0), (z0 + z1) / 2 + v.co.z * (z1 - z0)))
    return bm


def bevel_bm(bm, w, segs=1, angle=30, profile=0.5):
    es = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(angle)]
    if es:
        bmesh.ops.bevel(bm, geom=es, offset=w, segments=segs, affect="EDGES", profile=profile, clamp_overlap=True)
    return bm


def xform(bm, M4):
    bmesh.ops.transform(bm, matrix=M4, verts=bm.verts)
    return bm


def join_bm(bms):
    out = bmesh.new()
    for b in bms:
        me = bpy.data.meshes.new("tmpj")
        b.to_mesh(me)
        b.free()
        out.from_mesh(me)
        bpy.data.meshes.remove(me)
    return out


def set_mat(bm, key, pred=None):
    i = ORDER.index(key)
    for f in bm.faces:
        if pred is None or pred(f):
            f.material_index = i
    return bm


def rrect2(w0, w1, h0, h1, r, n=4):
    """Rounded rectangle outline as (u, v) pairs, counter-clockwise."""
    pts = []
    for (cu, cv, a0) in ((w1 - r, h1 - r, 0), (w0 + r, h1 - r, 90), (w0 + r, h0 + r, 180), (w1 - r, h0 + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cu + r * math.cos(a), cv + r * math.sin(a)))
    return pts


def rrect_yz(y0, y1, z0, z1, rt, rb, n=8):
    pts = []
    for (cy, cz, r, a0) in ((y1 - rt, z1 - rt, rt, 0), (y0 + rt, z1 - rt, rt, 90), (y0 + rb, z0 + rb, rb, 180), (y1 - rb, z0 + rb, rb, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cy + r * math.cos(a), cz + r * math.sin(a)))
    return pts


print("prims ok")
