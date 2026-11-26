def patch(p, pairs):
    s = open(p, encoding="utf-8").read()
    for a, b in pairs:
        assert a in s, a
        s = s.replace(a, b)
    open(p, "w", encoding="utf-8").write(s)

patch("n/b5_socket.py", [('frame = bent_plate(outer, 0.0050, 0.004, name="frame")', 'frame = bent_plate(outer, 0.0050, 0.004, hole=(0.0, SOCK_Z, 0.0425), name="frame")')])
patch("n/b1_shell.py", [('PROBES = {"dark": [(180, -45)], "stripe": [(150, 31.5)]}', 'PROBES = {"grey": [(180, -45)], "stripe": [(150, 31.5)]}')])
patch("n/b4_face.py", [("bar = capsule(256.0, 284.0, B_C[0], HWB, bar_plane(0.0026), bar_plane(-0.002), (0, 0, FZ))", "bar = capsule(256.0, 284.0, B_C[0], HWB, bar_plane(0.0036), bar_plane(-0.002), (0, 0, FZ))")])
print("patched 6")
