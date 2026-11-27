# Append the plug model (read-only source) into a temporary collection and measure its pins.
PLUG_BLEND = r"C:\Users\mesol\OneDrive\Documents\Art\2026\Alan's Bot Plugs\art\scene\plug.blend"
old_c = bpy.data.collections.get("tmp_plug")
if old_c:
    for o in list(old_c.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(old_c)
with bpy.data.libraries.load(PLUG_BLEND, link=False) as (src, dst):
    print("objects in plug.blend:", list(src.objects))
    dst.objects = list(src.objects)
tc = bpy.data.collections.new("tmp_plug")
scene.collection.children.link(tc)
for o in dst.objects:
    if o is not None:
        tc.objects.link(o)
bpy.context.view_layer.update()
for o in tc.objects:
    print(o.name, o.type, "parent", o.parent.name if o.parent else None, "loc", tuple(round(c, 4) for c in o.matrix_world.translation), "scale", tuple(round(c, 3) for c in o.scale))
    if o.type == "MESH":
        vs = [o.matrix_world @ v.co for v in o.data.vertices]
        mn = [min(v[i] for v in vs) for i in range(3)]
        mx = [max(v[i] for v in vs) for i in range(3)]
        print("   verts", len(vs), "bbox", [round(c, 4) for c in mn], [round(c, 4) for c in mx], "mats", [m.name if m else None for m in o.data.materials])
        # loose parts
        bm = bmesh.new(); bm.from_mesh(o.data)
        bm.verts.ensure_lookup_table()
        seen = set(); parts = []
        for v in bm.verts:
            if v.index in seen:
                continue
            st = [v]; seen.add(v.index); pts = []
            while st:
                w = st.pop(); pts.append(o.matrix_world @ w.co)
                for e in w.link_edges:
                    u = e.other_vert(w)
                    if u.index not in seen:
                        seen.add(u.index); st.append(u)
            parts.append(pts)
        for pts in sorted(parts, key=lambda p: -len(p))[:14]:
            mn = [min(v[i] for v in pts) for i in range(3)]
            mx = [max(v[i] for v in pts) for i in range(3)]
            print("     part n=%d  x %.4f..%.4f  y %.4f..%.4f  z %.4f..%.4f" % (len(pts), mn[0], mx[0], mn[1], mx[1], mn[2], mx[2]))
        bm.free()
