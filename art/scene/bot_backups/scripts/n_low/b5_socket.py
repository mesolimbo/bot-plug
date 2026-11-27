# ---- rear socket housing: frame, plate, socket ring + cup + pins, LED bar, hinge, flap -------------------
drop("socket_*", "flap", "hinge*")
R_H = 0.2592
SOCK_Z = 0.030


def xs(z):
    return -math.sqrt(R_H ** 2 - (z - C.z) ** 2)


def bent_plate(outline, front, depth, hole=None, name="plate"):
    """Extrude a (y, z) outline along +X by depth, optionally drill a round hole, slice every 8 mm in z and bend onto the back cylinder."""
    bm = bmesh.new()
    a = [bm.verts.new((0, y, z)) for y, z in outline]
    f = bm.faces.new(a)
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    bmesh.ops.translate(bm, vec=(depth, 0, 0), verts=[e for e in r["geom"] if isinstance(e, bmesh.types.BMVert)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = tmp_obj("tmp_" + name, bm)
    if hole:
        hy, hz, hr = hole
        cyl = bmesh.new()
        bmesh.ops.create_cone(cyl, cap_ends=True, segments=48, radius1=hr, radius2=hr, depth=0.1)
        xform(cyl, Matrix.Translation((0, hy, hz)) @ Matrix.Rotation(math.pi / 2, 4, "Y"))
        boolean(ob, tmp_obj("tmp_hole", cyl))
    bm = bmesh.new(); bm.from_mesh(ob.data)
    me = ob.data; bpy.data.objects.remove(ob, do_unlink=True); bpy.data.meshes.remove(me)
    zs = [v.co.z for v in bm.verts]
    z = math.ceil(min(zs) / 0.008) * 0.008
    while z < max(zs):
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, z), plane_no=(0, 0, 1), dist=1e-6)
        z += 0.008
    for v in bm.verts:
        v.co.x += xs(v.co.z) + front
    return bm


outer = [(y, z) for y, z in rrect_yz(-0.0685, 0.0685, -0.0265, 0.1265, 0.052, 0.013)]
frame = bent_plate(outer, 0.0050, 0.004, hole=(0.0, SOCK_Z, 0.0425), name="frame")
new_obj("socket_frame", frame, "body", "rubber", True, 30)

inner = [(y, z) for y, z in rrect_yz(-0.054, 0.054, -0.020, 0.108, 0.038, 0.008)]
plate = bent_plate(inner, 0.0, 0.008, hole=(0.0, SOCK_Z, 0.0434), name="plate")
bevel_bm(plate, 0.0012, 1, 50)
new_obj("socket_plate", plate, "body", "grey", True, 30)

# Socket barrel and orange ring are ONE solid: the ring is the raised lip of the barrel, separated from the dark
# barrel face by a 0.6 mm groove, with the material boundary on edge loops. Nothing overlaps or shares a face with it.
BOSS_X = -0.2600            # flat sealing face of the barrel, proud of the curved plate all the way round
RING_F = BOSS_X - 0.0012    # front of the orange ring
BORE = 0.0328               # clear bore (the plug body is r 30, its glow ring r 31.5)
GROOVE = BOSS_X + 0.0008
prof = [(BORE, -0.2280), (BORE, GROOVE), (BORE, RING_F + 0.0008), (BORE + 0.0009, RING_F), (0.0357, RING_F), (0.0366, RING_F + 0.0008), (0.0366, GROOVE),
        (0.0372, GROOVE), (0.0372, BOSS_X), (0.0405, BOSS_X), (0.0420, BOSS_X + 0.0015), (0.0420, -0.2280)]
boss = lathe(prof, (0, 0, SOCK_Z), "X", 64, close=True)
set_mat(boss, "dark")


def _ring_face(f):
    c = f.calc_center_median()
    return math.hypot(c.y, c.z - SOCK_Z) < 0.0367 and c.x < GROOVE - 0.0001


set_mat(boss, "light", _ring_face)
new_obj("socket_boss", boss, "body", None, True, 30)
FLOOR = -0.2385
# The cup floor is drilled where the three pin holes pass through it, and the drilled walls glow (as g/o_drill.py,
# g/p_norm.py and g/q9.py did by hand on the joined mesh).
PIN_YZ = [(0.0, 0.0120), (-0.0105, -0.0060), (0.0105, -0.0060)]
cup = bmesh.new()
bmesh.ops.create_cone(cup, cap_ends=True, segments=48, radius1=BORE + 0.0006, radius2=BORE + 0.0006, depth=0.004,
                      matrix=Matrix.Translation((FLOOR + 0.002, 0, SOCK_Z)) @ Matrix.Rotation(math.pi / 2, 4, "Y"))
cup_ob = tmp_obj("tmp_cup", cup)
drill = bmesh.new()
for py, pz in PIN_YZ:
    bmesh.ops.create_cone(drill, cap_ends=True, segments=24, radius1=0.004, radius2=0.004, depth=0.01,
                          matrix=Matrix.Translation((FLOOR + 0.002, py, SOCK_Z + pz)) @ Matrix.Rotation(math.pi / 2, 4, "Y"))
boolean(cup_ob, tmp_obj("tmp_drill", drill))
cup = bmesh.new(); cup.from_mesh(cup_ob.data)
me = cup_ob.data; bpy.data.objects.remove(cup_ob, do_unlink=True); bpy.data.meshes.remove(me)
bmesh.ops.recalc_face_normals(cup, faces=cup.faces)
set_mat(cup, "rubber")
set_mat(cup, "glow", lambda f: min(math.hypot(f.calc_center_median().y - py, f.calc_center_median().z - SOCK_Z - pz) for py, pz in PIN_YZ) < 0.0041)
new_obj("socket_cup", cup, "body", None, False)

# Cloverleaf receptacle (like an IEC C5/C6): one rounded lobe per pin, a hole in each lobe.
# Pin layout measured from scene/plug.blend: 3 pins, 7.0 mm diameter, 20 mm long (18 mm proud of the plug face),
# on a 12.1 mm radius at 120 degrees. In the game pose (plug origin at x -0.245, y 0, z 0.030, turned 180 deg about Z)
# the pins sit at (y, z - 0.030) = (0, +12), (-10.5, -6), (+10.5, -6) mm and reach x = -0.227.
PLUG_X = -0.2450
PINS = [(0.0, 0.0120), (-0.0105, -0.0060), (0.0105, -0.0060)]
PIN_R, HOLE_R = 0.0035, 0.0040
CLOVER_FRONT = PLUG_X + 0.0006           # 0.6 mm short of the seated plug face
HOLE_FLOOR = -0.2255                     # 19.5 mm deep holes for 18 mm pins


def clover_outline(lobe_r, core_r, k=0.0045, n=120):
    def sd(y, z):
        ds = [math.hypot(y - py, z - pz) - lobe_r for py, pz in PINS] + [math.hypot(y, z) - core_r]
        return -k * math.log(sum(math.exp(-d / k) for d in ds))       # smooth union: fillets where the lobes meet
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        lo, hi = 0.0, 0.03
        for _ in range(30):
            mid = 0.5 * (lo + hi)
            if sd(mid * math.cos(a), mid * math.sin(a)) < 0:
                lo = mid
            else:
                hi = mid
        pts.append((lo * math.cos(a), lo * math.sin(a)))
    return pts


o_full = clover_outline(0.0082, 0.0072, 0.0032)
o_rim = clover_outline(0.0074, 0.0064, 0.0032)
st = [[Vector((x, y, SOCK_Z + z)) for y, z in o] for x, o in ((HOLE_FLOOR + 0.001, o_full), (CLOVER_FRONT + 0.0009, o_full), (CLOVER_FRONT, o_rim))]
clover = tmp_obj("tmp_clover", strip_solid(st))
for py, pz in PINS:
    # one cutter per pin: the hole with its countersink, as a single lathe solid
    F_ = CLOVER_FRONT
    h = lathe([(0, F_ - 0.0030), (HOLE_R + 0.0042, F_ - 0.0030), (HOLE_R + 0.0012, F_), (HOLE_R, F_ + 0.0012), (HOLE_R, HOLE_FLOOR), (0, HOLE_FLOOR)], (0, py, SOCK_Z + pz), "X", 24)
    boolean(clover, tmp_obj("tmp_h", h))
cb = bmesh.new(); cb.from_mesh(clover.data)
me = clover.data; bpy.data.objects.remove(clover, do_unlink=True); bpy.data.meshes.remove(me)
bmesh.ops.remove_doubles(cb, verts=cb.verts, dist=1e-6)
set_mat(cb, "plastic")
# inside of the pin holes glows (as g/h_glow.py did on the joined mesh)
set_mat(cb, "glow", lambda f: f.calc_center_median().x > -0.2425 and min(math.hypot(f.calc_center_median().y - py, f.calc_center_median().z - SOCK_Z - pz) for py, pz in PINS) < 0.005)
new_obj("socket_clover", cb, "body", None, True, 30)

leds = []
for y0, y1 in ((-0.0155, -0.0058), (-0.0048, 0.0048), (0.0058, 0.0155)):
    b = box_bm(xs(0.084) - 0.0012, xs(0.084) + 0.002, y0, y1, 0.0768, 0.0912)
    bevel_bm(b, 0.0006, 1, 30)
    leds.append(b)
new_obj("socket_leds", join_bm(leds), "body", "light", False)
lb = box_bm(xs(0.084) - 0.0006, xs(0.084) + 0.002, -0.0185, 0.0185, 0.0738, 0.0942)
bevel_bm(lb, 0.0008, 1, 30)
new_obj("socket_led_bezel", lb, "body", "rubber", False)

# ---- hinged dust cover ---------------------------------------------------------------------------------
# Modelled in its CLOSED pose (covering the socket), as its own object whose origin is the hinge axis, then
# rotated about Y to hang open. FLAP_OPEN is the rest pose; set rotation_euler.y = 0 to close it.
HX, HZ = -0.2647, -0.0220                 # hinge axis (along Y)
FLAP_OPEN = math.radians(-205)
LID_R = 0.0400
LID_IN, LID_OUT = -0.2627, -0.2677       # inner (seal) face and outer face when closed


def cyl_y(x, z, r, y0, y1, segs=16):
    c = bmesh.new()
    bmesh.ops.create_cone(c, cap_ends=True, segments=segs, radius1=r, radius2=r, depth=abs(y1 - y0))
    return xform(c, Matrix.Translation((x, (y0 + y1) / 2, z)) @ Matrix.Rotation(math.pi / 2, 4, "X"))


lid = lathe([(0.0, LID_OUT), (LID_R - 0.0020, LID_OUT), (LID_R, LID_OUT + 0.0020), (LID_R, LID_IN - 0.0008), (LID_R - 0.0008, LID_IN), (0.0, LID_IN)], (0, 0, SOCK_Z), "X", 48)
seal = lathe([(0.0372, LID_IN - 0.0002), (0.0372, LID_IN + 0.0016), (0.0376, LID_IN + 0.0020), (0.0391, LID_IN + 0.0020), (0.0395, LID_IN + 0.0016), (0.0395, LID_IN - 0.0002)], (0, 0, SOCK_Z), "X", 48, close=True)
arm = box_bm(LID_OUT, LID_IN, -0.0150, 0.0150, HZ - 0.001, SOCK_Z - LID_R + 0.006)
bevel_bm(arm, 0.0012, 1, 30)
knuckle = cyl_y(HX, HZ, 0.0056, -0.0105, 0.0105)
tab = box_bm(LID_OUT - 0.0060, LID_OUT + 0.001, -0.0100, 0.0100, SOCK_Z + LID_R - 0.0065, SOCK_Z + LID_R - 0.0010)
bevel_bm(tab, 0.0014, 2, 30)
set_mat(lid, "dark"); set_mat(arm, "dark"); set_mat(knuckle, "steel"); set_mat(tab, "dark"); set_mat(seal, "rubber")
set_mat(lid, "steel", lambda f: math.hypot(f.calc_center_median().y, f.calc_center_median().z - SOCK_Z) > LID_R - 0.0026)
fb = join_bm([lid, seal, arm, knuckle, tab])
xform(fb, Matrix.Translation((-HX, 0, -HZ)))
flap = new_obj("flap", fb, "body", None, True, 30)
flap.location = (HX, 0, HZ)
flap.rotation_euler = (0, FLAP_OPEN, 0)

# body-side hinge: base plate on the housing, two arms with knuckles, and the pin
base = box_bm(-0.2420, -0.2330, -0.0320, 0.0320, HZ - 0.0120, HZ + 0.0100)
bevel_bm(base, 0.0015, 1, 30)
hp = [set_mat(base, "rubber")]
for sy in (-1, 1):
    a_ = box_bm(HX + 0.0010, -0.2350, sy * 0.0125, sy * 0.0270, HZ - 0.0056, HZ + 0.0056)
    bevel_bm(a_, 0.0012, 1, 30)
    hp.append(set_mat(a_, "rubber"))
    hp.append(set_mat(cyl_y(HX, HZ, 0.0056, sy * 0.0125, sy * 0.0270), "rubber"))
    hp.append(set_mat(cyl_y(HX, HZ, 0.0036, sy * 0.0270, sy * 0.0295, 12), "steel"))
hp.append(set_mat(cyl_y(HX, HZ, 0.0024, -0.0285, 0.0285, 12), "steel"))
new_obj("hinge", join_bm(hp), "body", None, True, 30)
print("socket ok")
