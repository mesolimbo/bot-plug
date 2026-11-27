def patch(p, pairs):
    s = open(p, encoding="utf-8").read()
    for a, b in pairs:
        assert a in s, (p, a)
        s = s.replace(a, b)
    open(p, "w", encoding="utf-8").write(s)

patch("n/b0_common.py", [('"light": mat("botn_light", (255, 140, 22), 0.3, 0.0, 2.4),', '"light": mat("botn_light", (255, 135, 20), 0.3, 0.0, 1.2),')])
patch("n/b10_render.py", [('"receptacle": ((-2, 0.5, 0.5), (-0.25, 0, 0.03), 0.09),',
    '"receptacle": ((-2, 0.5, 0.5), (-0.25, 0, 0.03), 0.09), "ring_straight": ((-2.26, 0, 0.03), (-0.26, 0, 0.03), 0.11),\n         "ring_oblique_side": ((-1.79, 1.286, 0.03), (-0.26, 0, 0.03), 0.11), "ring_oblique_above": ((-1.79, 0, 1.316), (-0.26, 0, 0.03), 0.11),')])
print("patched 13")
