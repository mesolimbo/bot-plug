# ---- face: bezel with light pockets, screen, amber pills, bottom bar, brow corner lights ------------------
drop("bezel", "screen", "pill*", "face_bar*", "corner_light*", "tmp_*")
FZ = 0.073
X0 = 0.2455           # bezel crest at mid height
TILT = 0.04           # bezel leans forward at the top, as measured (crest x: top 0.251, bottom 0.239)
SCR_R = 0.136
BEZ = [(0.1365, X0 - 0.0300), (0.1365, X0 - 0.0135), (0.1385, X0 - 0.0122), (0.1475, X0 - 0.0010), (0.1495, X0), (0.1525, X0), (0.1545, X0 - 0.0010),
       (0.1675, X0 - 0.0140), (0.1690, X0 - 0.0165), (0.1690, X0 - 0.0550)]


def bez_x(rho):
    """Bezel surface height (before the tilt) at radius rho."""
    P = BEZ[1:9]
    for (r0, x0), (r1, x1) in zip(P[:-1], P[1:]):
        if r0 <= rho <= r1:
            return x0 + (x1 - x0) * (rho - r0) / (r1 - r0)
    return P[0][1] if rho < P[0][0] else P[-1][1]


def shear(bm):
    for v in bm.verts:
        v.co.x += TILT * (v.co.z - FZ)
    return bm


# pill pockets at 3 and 9 o'clock: (start angle, end angle) in degrees from +Y towards +Z
PILLS = ((-21.0, 3.0), (177.0, 201.0))
P_R0, P_R1 = 0.1400, 0.1556          # pocket radial extent (inner lip to just past the crest)
P_DEPTH = 0.0036
GAP = 0.0011                         # dark gap between the pill and the pocket wall
RS = [P_R0 + (P_R1 - P_R0) * k / 8 for k in range(9)]

bz = lathe(BEZ, (0, 0, FZ), "X", 96, close=True)
bez_ob = tmp_obj("tmp_bezel", bz)
for a0, a1 in PILLS:
    pad = math.degrees(0.0 / 0.148)
    sect = [(P_R0, 0.30)] + [(r, bez_x(r) - P_DEPTH) for r in RS] + [(P_R1, 0.30)]
    boolean(bez_ob, tmp_obj("tmp_pocket", arc_solid(sect, (0, 0, FZ), "X", a0 - pad, a1 + pad, 12)))
bz = bmesh.new(); bz.from_mesh(bez_ob.data)
me = bez_ob.data; bpy.data.objects.remove(bez_ob, do_unlink=True); bpy.data.meshes.remove(me)
set_mat(bz, "paint")
set_mat(bz, "steel", lambda f: math.hypot(f.calc_center_median().y, f.calc_center_median().z - FZ) < 0.1486)


def in_pocket(f):
    c = f.calc_center_median()
    rho = math.hypot(c.y, c.z - FZ)
    ang = math.degrees(math.atan2(c.z - FZ, c.y)) % 360
    if not (P_R0 - 1e-4 <= rho <= P_R1 + 1e-4) or c.x > bez_x(rho) - 0.0004:
        return False
    return any(((a0 - 0.2) % 360 <= ang <= (a1 + 0.2) % 360) if (a0 % 360) < (a1 % 360) else (ang >= (a0 - 0.2) % 360 or ang <= (a1 + 0.2) % 360) for a0, a1 in PILLS)


set_mat(bz, "rubber", in_pocket)
new_obj("bezel", shear(bz), "body", None, True, 25)

SPH_R, SPH_C = 0.333, -0.0707
NR = 7                                    # was 14 rings on a 333 mm radius glass: 20 mm steps sag 0.15 mm
prof = [(0.1367 * k / NR, SPH_C + math.sqrt(SPH_R ** 2 - (0.1367 * k / NR) ** 2)) for k in range(NR + 1)]
scr = lathe(prof + [(0.1367, 0.2240), (0, 0.2240)], (0, 0, FZ), "X", 64)
uvl = scr.loops.layers.uv.new("UVMap")
for f in scr.faces:
    for l in f.loops:
        l[uvl].uv = (0.5 + l.vert.co.y / (2 * SCR_R), 0.5 + (l.vert.co.z - FZ) / (2 * SCR_R))
new_obj("screen", scr, "body", "screen", True, 0)


def capsule(a0, a1, rc, half_w, top_fn, bottom_fn, origin, axis="X", nseg=28, ncross=8, edge=0.0010):
    """A rounded-end light bar swept through angles a0..a1 at radius rc. top_fn(rho) / bottom_fn(rho) give its top and
    bottom along the sweep axis; half_w is the half width (the ends are semicircles of that radius)."""
    arc = math.radians(abs(a1 - a0)) * rc
    st = []
    for k in range(nseg + 1):
        t = k / nseg
        s = t * arc
        e = min(s, arc - s)                        # distance from the nearer end
        hw = half_w if e >= half_w else math.sqrt(max(half_w ** 2 - (half_w - e) ** 2, 0.0))
        hw = max(hw, 0.0006)
        a = math.radians(a0 + (a1 - a0) * t)
        row = []
        for j in range(ncross + 1):
            rho = rc - hw + 2 * hw * j / ncross
            drop_ = edge * (1 - min(1.0, min(j, ncross - j) / 1.0)) if hw > 0.002 else 0.0
            row.append((rho, top_fn(rho) - drop_))
        row += [(rc + hw, bottom_fn(rc + hw)), (rc - hw, bottom_fn(rc - hw))]
        e1, e2, ax = AXF[axis]
        st.append([Vector(origin) + e1 * (r * math.cos(a)) + e2 * (r * math.sin(a)) + ax * h for r, h in row])
    return strip_solid(st)


PRC, PHW = (P_R0 + P_R1) / 2, (P_R1 - P_R0) / 2 - GAP
for i, (a0, a1) in enumerate(PILLS):
    gap_deg = math.degrees(GAP / PRC)
    p = capsule(a0 + gap_deg, a1 - gap_deg, PRC, PHW, lambda r: bez_x(r) - 0.0003, lambda r: bez_x(r) - P_DEPTH - 0.0005, (0, 0, FZ))
    new_obj("pill%d" % i, shear(p), "body", "light", True, 35)

# amber bar at 6 o'clock: sits on the sloping underside just below the bezel, in its own dark tray (no tilt applied)
B_C = (0.1660, 0.2200)                    # centre (rho, x) of the bar section; the section slopes 45 degrees
B_T = (0.7071, -0.7071)                   # along the slope (outwards and back)
B_N = (0.7071, 0.7071)                    # out of the slope (down and forward)


def bar_plane(off):
    """(rho, x) -> x of a plane parallel to the bar slope, offset by `off` along the outward normal."""
    return lambda rho: B_C[1] + off / B_N[1] - (rho - B_C[0])


tray = arc_solid([(B_C[0] - 0.0088 * B_T[0] + 0.0010 * B_N[0], B_C[1] - 0.0088 * B_T[1] + 0.0010 * B_N[1]),
                  (B_C[0] + 0.0088 * B_T[0] + 0.0010 * B_N[0], B_C[1] + 0.0088 * B_T[1] + 0.0010 * B_N[1]),
                  (B_C[0] + 0.0088 * B_T[0] - 0.0100 * B_N[0], B_C[1] + 0.0088 * B_T[1] - 0.0100 * B_N[1]),
                  (B_C[0] - 0.0088 * B_T[0] - 0.0100 * B_N[0], B_C[1] - 0.0088 * B_T[1] - 0.0100 * B_N[1])], (0, 0, FZ), "X", 254.6, 285.4, 12)
bevel_bm(tray, 0.0009, 1, 40)
new_obj("face_bar_tray", tray, "body", "rubber", True, 35)
HWB = 0.0072 * B_T[0]                     # half width measured in rho
bar = capsule(256.0, 284.0, B_C[0], HWB, bar_plane(0.0036), bar_plane(-0.002), (0, 0, FZ))
new_obj("face_bar", bar, "body", "light", True, 35)

# corner lights: amber bars lying in the slots between the brow and the shoulder panels
kb = label_at(0, 37.5)
for i, sgn in enumerate((1, -1)):
    a, b = D(sgn * 26.4, 38.9), D(sgn * 20.6, 30.8)
    st = []
    for k in range(7):
        d = a.lerp(b, k / 6).normalized()
        s = d.cross((b - a).normalized()).normalized()
        r = samp(FIELD[kb], d) if kb >= 0 else samp(F_GLOB, d)
        st.append([C + d * (r - 0.0075) + s * 0.0030, C + d * (r - 0.0010) + s * 0.0030, C + d * (r - 0.0010) - s * 0.0030, C + d * (r - 0.0075) - s * 0.0030])
    cl = strip_solid(st)
    bevel_bm(cl, 0.0008, 1, 40)
    new_obj("corner_light%d" % i, cl, "body", "light", True, 40)
print("face ok")
