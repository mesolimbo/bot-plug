def patch(p, pairs):
    s = open(p, encoding="utf-8").read()
    for a, b in pairs:
        assert a in s, (p, a)
        s = s.replace(a, b)
    open(p, "w", encoding="utf-8").write(s)


patch("n/b10_render.py", [
    ('''lc = bpy.data.collections.get("botn_lights")
if not lc:
''', '''lc = bpy.data.collections.get("botn_lights")
if lc:
    for o in list(lc.objects):
        d = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.lights.remove(d)
    bpy.data.collections.remove(lc)
    lc = None
if not lc:
'''),
    ('light("key", "SUN", 3.2, (2.0, 1.6, 3.0))', 'light("key", "SUN", 1.45, (2.0, 1.6, 3.0))'),
    ('light("fill", "AREA", 90, (1.5, -2.2, 0.8), 2.5, (0.9, 0.95, 1.0))', 'light("fill", "AREA", 45, (1.5, -2.2, 0.8), 2.5, (0.9, 0.95, 1.0))'),
    ('light("rim", "AREA", 160, (-2.2, 0.6, 1.6), 2.0)', 'light("rim", "AREA", 70, (-2.2, 0.6, 1.6), 2.0)'),
    ('light("under", "AREA", 40, (0.3, 0.0, -1.8), 3.0)', 'light("under", "AREA", 22, (0.3, 0.0, -1.8), 3.0)'),
    ('world.node_tree.nodes["Background"].inputs[1].default_value = 0.55', 'world.node_tree.nodes["Background"].inputs[1].default_value = 0.45'),
    ('"leg": ((0.5, 3, -0.27), (0.02, 0.1, -0.27), 0.52),', '"leg": ((0.5, 3, -0.27), (0.02, 0.1, -0.27), 0.52), "top_rear_quarter": ((-1.6, -1.0, 1.9), (-0.06, -0.04, 0.3), 0.34),\n         "rear_above_vents": ((-1.8, 0.6, 1.5), (-0.1, 0.03, 0.28), 0.30), "top_front_quarter": ((1.6, 0.8, 1.7), (0.08, 0.04, 0.29), 0.34),\n         "receptacle": ((-2, 0.5, 0.5), (-0.25, 0, 0.03), 0.09),'),
])
patch("n/b0_common.py", [
    ('"light": mat("botn_light", (255, 160, 30), 0.3, 0.0, 5.0),', '"light": mat("botn_light", (255, 140, 22), 0.3, 0.0, 2.4),'),
    ('"stripe": mat("botn_stripe", (238, 178, 20), 0.5),', '"stripe": mat("botn_stripe", (232, 170, 16), 0.5),'),
    ('"paint": mat("botn_paint", (224, 212, 190), 0.5),', '"paint": mat("botn_paint", (222, 210, 188), 0.5),'),
])
patch("n/b9_final.py", [('b.inputs["Emission Strength"].default_value = 2.5', 'b.inputs["Emission Strength"].default_value = 1.8')])
print("patched 11")
