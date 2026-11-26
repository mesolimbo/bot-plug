import bpy
from mathutils import Vector
from collections import Counter
o = bpy.data.objects["bot_new"]; me = o.data
c = Vector((-0.245, 0, 0.03))
cnt = Counter()
xs = []
for p in me.polygons:
    q = o.matrix_world @ p.center
    if (Vector((0, q.y, q.z)) - Vector((0, c.y, c.z))).length < 0.03 and -0.30 < q.x < -0.20:
        cnt[(me.materials[p.material_index].name, round(q.x, 3))] += 1
for k, v in sorted(cnt.items(), key=lambda kv: kv[0][1]):
    print(k, v)
