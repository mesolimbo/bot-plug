import bpy, math
from collections import Counter
o = bpy.data.objects["bot_new"]; me = o.data
print([m.name if m else None for m in me.materials])
c = Counter()
for p in me.polygons:
    x = p.center
    if -0.2386 <= x.x <= -0.2344 and math.hypot(x.y, x.z - 0.03) < 0.0336:
        c[me.materials[p.material_index].name] += 1
print(c)
