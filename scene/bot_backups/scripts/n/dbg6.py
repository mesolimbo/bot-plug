sh = bpy.data.objects["shell"]
b = bmesh.new(); b.from_mesh(sh.data)
pl = b.faces.layers.int["panel"]
acc = {}
for f in b.faces:
    a = acc.setdefault(f[pl], [0, Vector((0,0,0)), 0.0])
    a[0] += 1; a[1] += (f.calc_center_median() - C).normalized(); a[2] += f.calc_area()
for k, a in sorted(acc.items()):
    print(k, a[0], tuple(round(c, 1) for c in lonlat(a[1])), "area cm2 %.1f" % (a[2] * 1e4))
bv = BVHTree.FromBMesh(b)
for lo, la in ((0, 37), (10, 37), (-10, 38), (0, 39)):
    h = bv.ray_cast(C + D(lo, la) * 0.5, -D(lo, la)); print(lo, la, h[0], h[3])
b.free()
