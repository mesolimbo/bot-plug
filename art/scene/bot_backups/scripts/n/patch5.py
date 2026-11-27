def patch(p, pairs):
    s = open(p, encoding="utf-8").read()
    for a, b in pairs:
        assert a in s, a
        s = s.replace(a, b)
    open(p, "w", encoding="utf-8").write(s)


patch("n/b1_shell.py", [
    ('''panel_layer = bm.faces.layers.int.new("panel")
bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
bm.verts.index_update(); bm.faces.index_update()
outer_v = {v for v in bm.verts if v.co.length > 0.985}
''', '''panel_layer = bm.faces.layers.int.new("panel")
outer_layer = bm.verts.layers.int.new("outer")
bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
bm.verts.index_update(); bm.faces.index_update()
outer_v = {v for v in bm.verts if v.co.length > 0.985}
for v in outer_v:
    v[outer_layer] = 1
'''),
    ("outer_v = {v for v in bm.verts if v.is_valid and (v.co - C).length > samp(F_GLOB, (v.co - C).normalized()) - 0.004}\n",
     "outer_v = {v for v in bm.verts if v[outer_layer]}\n"),
])
print("patched 5")
