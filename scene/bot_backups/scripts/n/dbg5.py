c = cone_cutter(top_loop, name="dbg_top")
b = bmesh.new(); b.from_mesh(c.data)
print("cutter verts", len(b.verts), "nonmanifold edges", sum(1 for e in b.edges if len(e.link_faces) != 2), "volume", b.calc_volume(signed=True))
mn = min((top_loop[i] - top_loop[(i + 1) % len(top_loop)]).length for i in range(len(top_loop)))
print("min step", mn, "n", len(top_loop))
cc = Vector((0, 0, 0))
for d in top_loop: cc += d
cc.normalize(); print("centre", lonlat(cc))
# angular monotonicity about cc
e1 = cc.orthogonal().normalized(); e2 = cc.cross(e1)
angs = [math.atan2(d.dot(e2), d.dot(e1)) for d in top_loop]
bad = 0
for i in range(len(angs)):
    da = (angs[(i + 1) % len(angs)] - angs[i] + math.pi) % (2 * math.pi) - math.pi
    if da < 0: bad += 1
print("backward steps", bad, "of", len(angs))
b.free()
me = c.data; bpy.data.objects.remove(c, do_unlink=True); bpy.data.meshes.remove(me)
