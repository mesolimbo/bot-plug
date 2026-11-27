# ---- dark core behind the panels (also the vent floor), hip-well walls, vent louvres and ribs -----------
drop("core*", "liner", "louvres", "vent_ribs", "cc_*")


def floor_r(lon):
    # measured on the old mesh: grille floor radius 0.259 at the front, 0.2475 at the rear
    return 0.25325 + 0.00575 * math.cos(math.radians(lon))


def core_r(d):
    lo, la = lonlat(d)
    r = samp(F_LOW, d) - 0.0070
    if la > 33:
        fl = floor_r(lo)
        if la > 58:
            fl -= 0.016 * min(1, (la - 58) / 6)
        t = min(1, (la - 33) / 4)
        r = r * (1 - t) + min(r, fl) * t
    return r


R_LINER = 0.155
# Was cube_sphere(44). Only the vent floor is in view (through the top opening, lat 35 to 67 with the step down under the collar);
# everything else sits behind the panels. So: 4.1 degree cells (22 a side), and the vent band alone split once more, which puts
# its vertices exactly where the 44-a-side sphere had them. The floor, and the line where the louvres meet it, stay as they were.
def core_sphere(n, lat0, lat1):
    q = math.pi / 4

    def warp(c):
        return Vector([math.tan(a_ * q) if abs(abs(a_) - 1) > 1e-6 else a_ for a_ in c]).normalized()
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=n - 1, use_grid_fill=True)
    band = [f for f in bm.faces if lat0 < lonlat(warp(f.calc_center_median()))[1] < lat1]
    bmesh.ops.subdivide_edges(bm, edges=list({e for f in band for e in f.edges}), cuts=1, use_grid_fill=True)
    for v in bm.verts:
        v.co = warp(v.co)
    return bm


bm = core_sphere(22, 35, 67)
bmesh.ops.triangulate(bm, faces=bm.faces, quad_method="SHORT_EDGE")      # flat faces for the exact boolean (see the shell)
core = tmp_obj("core_unit", bm)
for name, loop in OPENINGS:
    if name in ("face", "wellL", "wellR", "house"):
        boolean(core, cone_cutter(loop, r0=0.6, name="cc_" + name))
bm = bmesh.new(); bm.from_mesh(core.data)
me = core.data; bpy.data.objects.remove(core, do_unlink=True); bpy.data.meshes.remove(me)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
ng = [f for f in bm.faces if len(f.verts) > 4]
bmesh.ops.triangulate(bm, faces=ng)
for v in bm.verts:
    d = v.co.normalized()
    v.co = C + d * (core_r(d) if v.co.length > 0.9 else R_LINER)
new_obj("core", bm, "body", "rubber", True, 40)

# -- louvres: tilted blades standing on the vent floor --
def louvre(lon0, lon1, lat, name):
    n = max(4, int(abs(lon1 - lon0) / 3))
    st = []
    for k in range(n + 1):
        lo = lon0 + (lon1 - lon0) * k / n
        f = floor_r(lo)
        sec = [(lat - 0.45, f - 0.002), (lat + 0.0, f - 0.002), (lat + 1.05, f + 0.0055), (lat + 0.6, f + 0.0055)]
        st.append([C + D(lo, la) * r for la, r in sec])
    return strip_solid(st)


lv = []
for k in range(8):                     # front: 8 louvres at 8.6 mm pitch (old: 8 painted slats between x 135 and 195 mm)
    la = 41.8 + k * 2.37
    half = min(27 + (la - 40) * 1.9, 48) + 2 if la < 50.5 else 64
    lv.append(louvre(-half, half, la, "lf"))
for k in range(6):                     # rear: 6 louvres at 6.3 mm pitch
    la = 44.2 + k * 2.1
    lv.append(louvre(146.5, 213.5 + (la - 42) * 1.05, la, "lb"))
for la in (48.0, 50.2):
    lv.append(louvre(74, 137, la, "ls"))
new_obj("louvres", join_bm(lv), "body", "dark", True, 30)

# -- ribs: steel bars across the grilles --
def rib(a, b, w=0.0052, h0=-0.002, h1=0.0105):
    da, db = D(*a), D(*b)
    n = 8
    st = []
    for k in range(n + 1):
        d = da.lerp(db, k / n).normalized()
        t = (db - da).normalized()
        s = d.cross(t).normalized()
        f = floor_r(lonlat(d)[0])
        st.append([C + d * (f + h0) + s * (w / 2), C + d * (f + h1) + s * (w / 2), C + d * (f + h1) - s * (w / 2), C + d * (f + h0) - s * (w / 2)])
    return strip_solid(st)


# Measured on the old mesh: front ribs 11.5 mm wide, 7.5 mm proud of the grille floor, centred y = +-32 mm; angled side ribs 7.5 mm wide;
# rear ribs 10.5 mm wide, 9 mm proud, centred y = 0 and +-58 mm.
ribs = [rib((9.4, 40.3), (13.7, 59.2), 0.0115, -0.002, 0.0074), rib((-9.4, 40.3), (-13.7, 59.2), 0.0115, -0.002, 0.0074),
        rib((22.0, 40.0), (37.5, 57.8), 0.0075, -0.002, 0.0066), rib((-22.0, 40.0), (-37.5, 57.8), 0.0075, -0.002, 0.0066),
        rib((180, 41.2), (180, 58.5), 0.0105, -0.002, 0.0090), rib((161.6, 41.2), (154.6, 58.5), 0.0105, -0.002, 0.0090), rib((198.4, 41.2), (205.4, 58.5), 0.0105, -0.002, 0.0090)]
for r_ in ribs:
    bevel_bm(r_, 0.0009, 1, 40)
new_obj("vent_ribs", join_bm(ribs), "body", "steel", True, 30)
print("core ok %.1f" % (time.time() - T0))
