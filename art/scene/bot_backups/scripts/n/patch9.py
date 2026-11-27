def patch(p, pairs):
    s = open(p, encoding="utf-8").read()
    for a, b in pairs:
        assert a in s, (p, a)
        s = s.replace(a, b)
    open(p, "w", encoding="utf-8").write(s)


s = open("n/b3_top.py", encoding="utf-8").read()
a = s.index("# dark ring floor with teeth")
b = s.index("# collar: inner lip is a circle")
s = s[:a] + '''# dark toothed ring: ONE solid. The floor ring carries 22 evenly spaced teeth of equal height, with upright sides.
NT = 22
R_IN, R_OUT, T_IN, T_OUT = 0.0860, 0.1262, 0.0935, 0.1175
Z_FLOOR, Z_TOOTH, Z_BASE = -0.0190, -0.0150, -0.0260
st = []
eps = math.radians(0.12)
for k in range(NT):
    a0 = 2 * math.pi * k / NT
    a1 = a0 + 2 * math.pi / NT * 0.58
    for ang, h in ((a0 - eps, Z_FLOOR + 0.0002), (a0 + eps, Z_TOOTH), (a1 - eps, Z_TOOTH), (a1 + eps, Z_FLOOR + 0.0002)):
        c, s_ = math.cos(ang), math.sin(ang)
        st.append([Vector((r * c, r * s_, z)) for r, z in ((R_IN, Z_FLOOR), (T_IN, Z_FLOOR), (T_IN + 0.0008, h), (T_OUT - 0.0008, h), (T_OUT, Z_FLOOR), (R_OUT, Z_FLOOR), (R_OUT, Z_BASE), (R_IN, Z_BASE))])
ring = strip_solid(st, closed=True)
set_mat(ring, "dark")
set_mat(ring, "rubber", lambda f: all(v.co.z < Z_FLOOR + 0.0005 for v in f.verts))
new_obj("top_ring", xform(ring, TOP_M), "body", None, True, 30)

''' + s[b:]
s = s.replace('drop("dome", "top_ring", "ring_teeth", "collar", "lug*", "antenna*")', 'drop("dome", "top_ring", "ring_teeth", "collar", "lug*", "antenna*")')
open("n/b3_top.py", "w", encoding="utf-8").write(s)
# collar: one closed solid whose outer wall overlaps the shell edge by 3 mm and stands clear above it (no coincident surfaces)
patch("n/b3_top.py", [
    ("COL_C, COL_RX, COL_RY = 0.012, 0.139, 0.150", "COL_C, COL_RX, COL_RY = 0.012, 0.142, 0.153"),
    ("collar = lathe([(0.1225, -0.0195), (0.1225, -0.0135), (0.1240, -0.0120), (1.0 - 0.0015, -0.0325), (1.0, -0.0340), (1.0, -0.0470), (0.1225, -0.0470)]",
     "collar = lathe([(0.1250, -0.0230), (0.1250, -0.0135), (0.1265, -0.0120), (1.0 - 0.0015, -0.0290), (1.0, -0.0305), (1.0, -0.0560), (0.1250, -0.0560)]"),
])
print("patched 9")
