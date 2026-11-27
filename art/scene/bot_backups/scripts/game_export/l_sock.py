import bpy, math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import bmesh
o = bpy.data.objects["bot_new"]; me = o.data
bm = bmesh.new(); bm.from_mesh(me); bm.transform(o.matrix_world); bm.faces.ensure_lookup_table()
bvh = BVHTree.FromBMesh(bm)
# shoot rays along +X down each pin hole axis and list every surface crossed
for y, z in [(0.0, 0.042), (-0.0105, 0.024), (0.0105, 0.024)]:
    hits = []
    org = Vector((-0.30, y + 0.0015, z + 0.001)); d = Vector((1, 0, 0))
    while True:
        h = bvh.ray_cast(org, d, 0.2)
        if h[0] is None: break
        f = bm.faces[h[2]]
        hits.append((round(h[0].x, 4), me.materials[f.material_index].name))
        org = h[0] + d * 1e-5
        if len(hits) > 12: break
    print((y, z), hits)
