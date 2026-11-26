# ---- legs: hip drum, thigh link, knee and ankle wheels, shin bar, boot. Each part rides one bone. -------
drop("hip*", "thigh*", "knee*", "shin*", "ankle*", "toe*", "heel*", "sole*", "foot*", "boot*")
rigd = rig.data
BV = 0.0022       # edge chamfer on leg plates


def cut(bm, co, no):
    """Slice off everything on the +no side of a plane and cap the cut."""
    r = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no, clear_outer=True, dist=1e-6)
    es = [e for e in r["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
    if es:
        bmesh.ops.holes_fill(bm, edges=es)
    return bm


def ngon_y(c, rflat, y0, y1, n=8, ch=0.0, rot=None):
    """n-gon prism along Y, flats axis-aligned; ch chamfers both end faces."""
    rc = rflat / math.cos(math.pi / n)
    rot = math.pi / n if rot is None else rot
    def ringp(r, y):
        return [Vector((c.x + r * math.cos(rot + 2 * math.pi * k / n), y, c.z + r * math.sin(rot + 2 * math.pi * k / n))) for k in range(n)]
    s = 1 if y1 > y0 else -1
    if ch:
        st = [ringp(rc - ch, y0), ringp(rc, y0 + s * ch), ringp(rc, y1 - s * ch), ringp(rc - ch, y1)]
    else:
        st = [ringp(rc, y0), ringp(rc, y1)]
    return strip_solid(st)


def bolts(points, normal, r=0.0036, h=0.0016):
    out = []
    for p in points:
        b = bmesh.new()
        bmesh.ops.create_cone(b, cap_ends=True, segments=10, radius1=r, radius2=r * 0.8, depth=h * 2)
        q = Vector(normal).normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()
        xform(b, Matrix.Translation(p) @ q)
        out.append(b)
    return join_bm(out)


for side, sg in (("L", 1), ("R", -1)):
    Hh, K, A = [rigd.bones[f"{b}.{side}"].head_local.copy() for b in ("thigh", "shin", "foot")]
    y0 = Hh.y
    Yv = Vector((0, 1, 0))

    def frame(a, b):
        u = b - a; u.y = 0; u.normalize()
        return u, Vector((-u.z, 0, u.x))

    def slab(prof, a, b, w, name, bone, m="paint", bv=BV):
        u, n = frame(a, b)
        st = [[Vector((a.x, y0 + sg * ww, a.z)) + u * s + n * t for s, t in prof] for ww in (-w, w)]
        bm = strip_solid(st)
        bevel_bm(bm, bv, 2, 30)
        return new_obj(f"{name}.{side}", bm, bone, m, True, 28)

    # --- thigh bone ---
    tb = f"thigh.{side}"
    u, n = frame(Hh, K)
    HC = Vector((Hh.x, 0, Hh.z)) + u * 0.045 + n * (-0.0134)       # hip drum centre (below the pivot, as on the old model)
    HR = 0.0535
    drum = lathe([(0, -0.083), (0.030, -0.083), (0.030, -0.059), (HR - 0.004, -0.059), (HR, -0.055), (HR, 0.062), (HR - 0.004, 0.066), (0.046, 0.066), (0.044, 0.0625),
                  (0.034, 0.0625), (0.032, 0.066), (0, 0.066)], (HC.x, y0, HC.z), "Y", 40, rfun=lambda a, r, h: (r, sg * h))
    hub = lathe([(0.0, 0.0745), (0.0075, 0.0745), (0.0085, 0.0735), (0.0085, 0.071), (0.028, 0.071), (0.031, 0.068), (0.031, 0.060), (0, 0.060)], (HC.x, y0, HC.z), "Y", 32, rfun=lambda a, r, h: (r, sg * h))
    set_mat(drum, "dark"); set_mat(hub, "paint")
    set_mat(hub, "steel", lambda f: math.hypot(f.calc_center_median().x - HC.x, f.calc_center_median().z - HC.z) < 0.0086)
    new_obj(f"hip_drum.{side}", join_bm([drum, hub]), tb, None, True, 28)
    # link: tangent to the drum at the top, 73 mm wide with chamfered corners at the knee end
    slab([(0.047, 0.0395), (0.150, 0.0365), (0.1655, 0.0265), (0.1655, -0.0265), (0.150, -0.0365), (0.060, -0.0640), (0.030, -0.0600), (0.020, 0.0200)], Hh, K, 0.040, "thigh", tb)
    bp = []
    for t in (-0.020, 0.020):
        bp.append(Vector((Hh.x, y0 + sg * 0.040, Hh.z)) + u * 0.152 + n * t)
    b1 = bolts(bp, (0, sg, 0))
    bpf = [Vector((Hh.x, y0 + sg * w, Hh.z)) + u * 0.140 + n * 0.0365 for w in (-0.023, 0.023)]
    b2 = bolts(bpf, n)
    new_obj(f"thigh_bolts.{side}", join_bm([b1, b2]), tb, "steel", True, 30)

    # --- knee (rides the shin) and ankle (rides the foot) ---
    def wheel_joint(c, name, bone, capw):
        cc = Vector((c.x, 0, c.z))
        barrel = lathe([(0.0, -0.0285), (0.0300, -0.0285), (0.0300, -0.0200), (0.0285, -0.0185), (0.0285, -0.0165), (0.0300, -0.0150), (0.0300, 0.0150), (0.0285, 0.0165), (0.0285, 0.0185),
                        (0.0300, 0.0200), (0.0300, 0.0285), (0.0, 0.0285)], (c.x, y0, c.z), "Y", 32)
        parts = [set_mat(barrel, "dark")]
        for s2 in (-1, 1):
            parts.append(set_mat(ngon_y(cc, 0.0370, y0 + s2 * 0.0275, y0 + s2 * 0.0372, 8, 0.0018), "dark"))
            parts.append(set_mat(ngon_y(cc, 0.0283, y0 + s2 * 0.0365, y0 + s2 * capw, 8, 0.0030), "paint"))
            pin = lathe([(0.0, capw + 0.0035), (0.0050, capw + 0.0035), (0.0064, capw + 0.0022), (0.0064, capw - 0.002), (0, capw - 0.002)], (c.x, y0, c.z), "Y", 16, rfun=lambda a, r, h, s2=s2: (r, s2 * h))
            parts.append(set_mat(pin, "steel"))
        return new_obj(f"{name}.{side}", join_bm(parts), bone, None, True, 28)

    wheel_joint(K, "knee", f"shin.{side}", 0.0510)
    wheel_joint(A, "ankle", f"foot.{side}", 0.0490)

    # --- shin bar: straight edges, the front edge splays 8 mm toward the ankle as on the old one ---
    sb = f"shin.{side}"
    us, ns = frame(K, A)
    slab([(0.030, -0.0125), (0.0375, -0.0205), (0.139, -0.0190), (0.1465, -0.0115), (0.1465, 0.0340), (0.138, 0.0425), (0.0375, 0.0345), (0.030, 0.0270)], K, A, 0.0385, "shin", sb)
    bp = [Vector((K.x, y0 + sg * 0.0385, K.z)) + us * s + ns * t for s, t in ((0.046, -0.010), (0.046, 0.024), (0.131, -0.008), (0.131, 0.031))]
    bpf = [Vector((K.x, y0 + sg * w, K.z)) + us * s + ns * (0.0345 + (s - 0.0375) * 0.0796) for w in (-0.023, 0.023) for s in (0.048, 0.128)]
    nf = (ns - us * 0.0796).normalized()
    new_obj(f"shin_bolts.{side}", join_bm([bolts(bp, (0, sg, 0)), bolts(bpf, nf)]), sb, "steel", True, 30)

    # --- boot (foot bone): toe block, heel block, dark sole with bridge, dark ankle yoke ---
    fb = f"foot.{side}"
    WB = 0.0655

    def block(prof, w, taper, corner_x, name, m="paint", bv=0.0028):
        st = [[Vector((x, y0 + ww, z)) for x, z in prof] for ww in (-w, w)]
        bm = strip_solid(st)
        if taper:
            (z0, w0), (z1, w1) = taper
            for s2 in (-1, 1):
                nrm = Vector((0, s2 * (z1 - z0), (w0 - w1))).normalized()
                cut(bm, (0, y0 + s2 * w0, z0), nrm)
        if corner_x is not None:
            xc, dirx, c = corner_x
            for s2 in (-1, 1):
                cut(bm, (xc, y0 + s2 * (w - c), 0), Vector((dirx, s2, 0)).normalized())
        bevel_bm(bm, bv, 2, 25)
        return new_obj(f"{name}.{side}", bm, fb, m, True, 28)

    block([(0.1555, -0.4640), (0.1510, -0.4915), (0.0300, -0.4915), (0.0100, -0.4450), (0.0120, -0.4280), (0.0400, -0.4020), (0.0600, -0.3920)],
          WB, ((-0.4620, 0.0650), (-0.3920, 0.0365)), (0.1555, 1, 0.014), "toe")
    block([(-0.0080, -0.4915), (-0.0080, -0.4670), (-0.0200, -0.4360), (-0.0550, -0.4100), (-0.1090, -0.4600), (-0.1170, -0.4915)],
          WB, ((-0.4600, 0.0650), (-0.4100, 0.0330)), (-0.1170, -1, 0.012), "heel")
    sole = strip_solid([[Vector((x, y0 + ww, z)) for x, z in ((0.1535, -0.4925), (0.1480, -0.5000), (-0.1130, -0.5000), (-0.1180, -0.4925), (-0.1180, -0.4900), (0.1535, -0.4900))] for ww in (-0.064, 0.064)])
    for s2 in (-1, 1):
        cut(sole, (0.1535, y0 + s2 * 0.050, 0), Vector((1, s2, 0)).normalized())
        cut(sole, (-0.1180, y0 + s2 * 0.052, 0), Vector((-1, s2, 0)).normalized())
    bridge = strip_solid([[Vector((x, y0 + ww, z)) for x, z in ((0.034, -0.4910), (0.034, -0.4690), (-0.012, -0.4690), (-0.012, -0.4910))] for ww in (-0.050, 0.050)])
    bevel_bm(bridge, 0.002, 1, 30)
    yoke = strip_solid([[Vector((x, y0 + ww, z)) for x, z in ((0.0340, -0.4600), (0.0340, -0.4180), (0.0190, -0.4140), (0.0020, -0.4300), (0.0000, -0.4600))] for ww in (-0.041, 0.041)])
    bevel_bm(yoke, 0.002, 1, 30)
    new_obj(f"sole.{side}", join_bm([sole, bridge, yoke]), fb, "rubber", True, 28)
print("legs ok")
