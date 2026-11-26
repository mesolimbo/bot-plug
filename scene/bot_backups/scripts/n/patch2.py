p = "n/b5_socket.py"
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert a in s, a
    s = s.replace(a, b)


# ring: bore opened to 32.8 mm radius so the plug's own glow ring (r 31.5) clears it
rep("ring = lathe([(0.0316, XR + 0.0040), (0.0316, XR - 0.0012), (0.0326, XR - 0.0022), (0.0352, XR - 0.0022), (0.0362, XR - 0.0010), (0.0362, XR + 0.0040)]",
    "ring = lathe([(0.0328, XR + 0.0040), (0.0328, XR - 0.0012), (0.0336, XR - 0.0022), (0.0358, XR - 0.0022), (0.0368, XR - 0.0010), (0.0368, XR + 0.0040)]")
rep("boss = lathe([(0.0316, BOSS_X), (0.0405, BOSS_X)", "boss = lathe([(0.0328, BOSS_X), (0.0405, BOSS_X)")
a = s.index("FLOOR = -0.2400")
b = s.index("leds = []")
s = s[:a] + '''FLOOR = -0.2385
cup = lathe([(0.0328, XR + 0.0030), (0.0328, FLOOR), (0, FLOOR)], (0, 0, SOCK_Z), "X", 48)
if sum(f.normal.x for f in cup.faces if abs(f.normal.x) > 0.9) > 0:
    bmesh.ops.reverse_faces(cup, faces=cup.faces)
new_obj("socket_cup", cup, "body", "rubber", True, 30)

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


o_full = clover_outline(0.0086, 0.0090)
o_rim = clover_outline(0.0078, 0.0082)
st = [[Vector((x, y, SOCK_Z + z)) for y, z in o] for x, o in ((HOLE_FLOOR + 0.001, o_full), (CLOVER_FRONT + 0.0009, o_full), (CLOVER_FRONT, o_rim))]
clover = tmp_obj("tmp_clover", strip_solid(st))
for py, pz in PINS:
    h = bmesh.new()
    bmesh.ops.create_cone(h, cap_ends=True, segments=24, radius1=HOLE_R, radius2=HOLE_R, depth=0.04)
    xform(h, Matrix.Translation((HOLE_FLOOR - 0.02, py, SOCK_Z + pz)) @ Matrix.Rotation(math.pi / 2, 4, "Y"))
    xform(h, Matrix.Translation((0, 0, 0)))
    cs = bmesh.new()                                                 # countersink
    bmesh.ops.create_cone(cs, cap_ends=True, segments=24, radius1=HOLE_R + 0.0030, radius2=HOLE_R - 0.0010, depth=0.004)
    xform(cs, Matrix.Translation((CLOVER_FRONT - 0.0008, py, SOCK_Z + pz)) @ Matrix.Rotation(math.pi / 2, 4, "Y"))
    boolean(clover, tmp_obj("tmp_h", h))
    boolean(clover, tmp_obj("tmp_cs", cs))
cb = bmesh.new(); cb.from_mesh(clover.data)
me = clover.data; bpy.data.objects.remove(clover, do_unlink=True); bpy.data.meshes.remove(me)
new_obj("socket_clover", cb, "body", "rubber", True, 30)

''' + s[b:]
open(p, "w", encoding="utf-8").write(s)

p = "n/b2_core.py"
s = open(p, encoding="utf-8").read()
rep('    if name in ("face", "wellL", "wellR"):', '    if name in ("face", "wellL", "wellR", "house"):')
open(p, "w", encoding="utf-8").write(s)
print("patched 2")
