import bpy, bmesh
from collections import Counter
o = bpy.data.objects["bot_new"]
bm = bmesh.new(); bm.from_mesh(o.data); bm.faces.ensure_lookup_table()
seen = set(); parts = []
for f in bm.faces:
    if f.index in seen: continue
    stack = [f]; seen.add(f.index); faces = []
    while stack:
        g = stack.pop(); faces.append(g)
        for e in g.edges:
            for h in e.link_faces:
                if h.index not in seen:
                    seen.add(h.index); stack.append(h)
    t = sum(len(x.verts) - 2 for x in faces)
    mats = Counter(o.data.materials[x.material_index].name for x in faces).most_common(1)[0][0]
    c = sum((x.calc_center_median() for x in faces), faces[0].calc_center_median() * 0) / len(faces)
    parts.append((t, mats, tuple(round(v, 3) for v in c)))
parts.sort(reverse=True)
print("parts", len(parts), "total", sum(p[0] for p in parts))
for p in parts[:30]: print(p)
print("under 500 tris:", sum(1 for p in parts if p[0] < 500), sum(p[0] for p in parts if p[0] < 500))
