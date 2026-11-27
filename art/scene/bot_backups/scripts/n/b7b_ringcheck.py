# ---- intersection check: the orange ring faces against every neighbouring part -------------------------------
import json
bo = bpy.data.objects["socket_boss"]
li = ORDER.index("light")


def tri_bvh(ob, keep=None):
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.transform(bm, matrix=ob.matrix_world, verts=bm.verts)
    if keep is not None:
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if not keep(f)], context="FACES")
    bmesh.ops.triangulate(bm, faces=bm.faces)
    t = BVHTree.FromBMesh(bm, epsilon=0.0)
    n = len(bm.faces)
    bm.free()
    return t, n


ring, nr = tri_bvh(bo, lambda f: f.material_index == li)
res = {}
for ob in coll().objects:
    if ob.type != "MESH" or ob is bo or ob.name.startswith(("tmp", "cut_", "cc_")):
        continue
    bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    if min(v.x for v in bb) > -0.2 or max(abs(v.y) for v in bb) < 0 or min(v.z for v in bb) > 0.12 or max(v.z for v in bb) < -0.06:
        continue
    t, n = tri_bvh(ob)
    res[ob.name] = len(ring.overlap(t))
print("ring faces (triangles):", nr)
for k, v in sorted(res.items()):
    print("  ring x %-18s intersecting triangle pairs: %d" % (k, v))
print("total intersecting pairs:", sum(res.values()))
json.dump(res, open(SP + r"\n\ring_check.json", "w"), indent=1)
