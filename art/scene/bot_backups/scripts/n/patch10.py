def patch(p, pairs):
    s = open(p, encoding="utf-8").read()
    for a, b in pairs:
        assert a in s, (p, a)
        s = s.replace(a, b)
    open(p, "w", encoding="utf-8").write(s)


patch("n/b0b_prims.py", [
    ("def box_bm(x0, x1, y0, y1, z0, z1):\n    bm = bmesh.new()",
     "def box_bm(x0, x1, y0, y1, z0, z1):\n    x0, x1 = min(x0, x1), max(x0, x1)\n    y0, y1 = min(y0, y1), max(y0, y1)\n    z0, z1 = min(z0, z1), max(z0, z1)\n    bm = bmesh.new()"),
])
s = open("n/b5_socket.py", encoding="utf-8").read()
a = s.index("for py, pz in PINS:\n    h = bmesh.new()")
b = s.index("cb = bmesh.new(); cb.from_mesh(clover.data)")
s = s[:a] + '''for py, pz in PINS:
    # one cutter per pin: the hole with its countersink, as a single lathe solid
    F_ = CLOVER_FRONT
    h = lathe([(0, F_ - 0.0030), (HOLE_R + 0.0042, F_ - 0.0030), (HOLE_R + 0.0012, F_), (HOLE_R, F_ + 0.0012), (HOLE_R, HOLE_FLOOR), (0, HOLE_FLOOR)], (0, py, SOCK_Z + pz), "X", 24)
    boolean(clover, tmp_obj("tmp_h", h))
''' + s[b:]
s = s.replace('''new_obj("socket_clover", cb, "body", "plastic", True, 30)''', '''bmesh.ops.remove_doubles(cb, verts=cb.verts, dist=1e-6)
new_obj("socket_clover", cb, "body", "plastic", True, 30)''')
open("n/b5_socket.py", "w", encoding="utf-8").write(s)
print("patched 10")
