def patch(p, pairs):
    s = open(p, encoding="utf-8").read()
    for a, b in pairs:
        assert a in s, a
        s = s.replace(a, b)
    open(p, "w", encoding="utf-8").write(s)


patch("n/b1_shell.py", [
    ("# crisp lip: a small hard chamfer where each panel top turns into its edge wall\n",
     "# crisp lip: a small hard chamfer where each panel top turns into its edge wall\n"
     "bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0007)     # merge the tiny edges the cuts leave, so the chamfer stays even\n"
     "outer_v = {v for v in bm.verts if v.is_valid and (v.co - C).length > samp(F_GLOB, (v.co - C).normalized()) - 0.004}\n"),
    ("print(\"fields %.1fs\" % (time.time() - T0))",
     "# lowest panel surface around each direction: the dark core sits below this, so it never shows through a recessed panel\n"
     "F_LAB = F_GLOB.copy()\n"
     "for k in keep_ids:\n"
     "    F_LAB = np.where(LABEL == k, FIELD[k], F_LAB)\n"
     "F_LOW = F_LAB\n"
     "for _ in range(7):\n"
     "    F_LOW = _minmax(F_LOW, np.minimum)\n"
     "F_LOW = np.minimum(blur(F_LOW, 1.2), F_GLOB)\n"
     "print(\"fields %.1fs\" % (time.time() - T0))"),
])
patch("n/b2_core.py", [("    r = samp(F_GLOB, d) - 0.0065\n", "    r = samp(F_LOW, d) - 0.0070\n")])
patch("n/b5_socket.py", [('new_obj("socket_clover", cb, "body", "rubber", True, 30)', 'new_obj("socket_clover", cb, "body", "plastic", True, 30)')])
patch("n/b0_common.py", [
    ('"stripe", "rubber", "grey"]', '"stripe", "rubber", "grey", "plastic"]'),
    ('        "grey": mat("botn_grey", (84, 82, 84), 0.5, 0.2),', '        "grey": mat("botn_grey", (84, 82, 84), 0.5, 0.2),\n        "plastic": mat("botn_plastic", (58, 58, 62), 0.75),'),
])
print("patched 4")
