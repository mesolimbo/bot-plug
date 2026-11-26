import bpy, bmesh, math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
o = bpy.data.objects["bot_new"]; me = o.data
bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
bvh = BVHTree.FromBMesh(bm)
h = bvh.ray_cast(Vector((-0.30, 0.0015, 0.043)), Vector((1, 0, 0)), 0.2)
s = bm.faces[h[2]]
st = [s]; seen = {s.index}; fs = []
while st:
    g = st.pop(); fs.append(g)
    for e in g.edges:
        for k in e.link_faces:
            if k.index not in seen: seen.add(k.index); st.append(k)
vs = {v for f in fs for v in f.verts}
xs = [v.co.x for v in vs]; rs = [math.hypot(v.co.y, v.co.z - 0.03) for v in vs]
from collections import Counter
print("part faces", len(fs), "x %.4f..%.4f" % (min(xs), max(xs)), "r %.4f..%.4f" % (min(rs), max(rs)), Counter(me.materials[f.material_index].name for f in fs))
for f in fs[:0]: pass
print("hit face verts", len(s.verts), "centre", tuple(round(c, 4) for c in s.calc_center_median()))
