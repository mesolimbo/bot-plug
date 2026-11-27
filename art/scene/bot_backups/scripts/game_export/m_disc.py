import bpy, bmesh, math
from mathutils import Vector
DELETE = globals().get("DELETE", False)
o = bpy.data.objects["bot_new"]; me = o.data
bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
mw = o.matrix_world
W = lambda c: mw @ c
print('matrix identity', mw == mw.Identity(4))
pins = [(0.0, 0.042), (-0.0105, 0.024), (0.0105, 0.024)]
rub = [x.name for x in me.materials].index("botn_rubber")
seeds = [f for f in bm.faces if f.material_index == rub and -0.240 < W(f.calc_center_median()).x < -0.233
         and min(math.hypot(W(f.calc_center_median()).y - y, W(f.calc_center_median()).z - z) for y, z in pins) < 0.004]
seen = set(); parts = []
for s in seeds:
    if s.index in seen: continue
    st = [s]; seen.add(s.index); fs = []
    while st:
        g = st.pop(); fs.append(g)
        for e in g.edges:
            for h in e.link_faces:
                if h.index not in seen: seen.add(h.index); st.append(h)
    vs = {v for f in fs for v in f.verts}
    xs = [W(v.co).x for v in vs]; rs = [min(math.hypot(W(v.co).y - y, W(v.co).z - z) for y, z in pins) for v in vs]
    parts.append(fs)
    print("part faces", len(fs), "x %.4f..%.4f" % (min(xs), max(xs)), "r from pin axis %.4f..%.4f" % (min(rs), max(rs)),
          "mats", {me.materials[f.material_index].name for f in fs})
if DELETE:
    bmesh.ops.delete(bm, geom=[f for fs in parts for f in fs], context="FACES")
    bm.to_mesh(me); me.update(); print("deleted", sum(len(p) for p in parts))
bm.free()
