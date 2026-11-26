import bpy, math
o = bpy.data.objects["bot_new"]; me = o.data
n = [m.name if m else None for m in me.materials]
fix = {n.index("botn_stripe"): n.index("botn_rubber"), n.index("botn_plastic"): n.index("bot_glow")}
k = 0
for p in me.polygons:
    x = p.center
    if -0.2386 <= x.x <= -0.2344 and math.hypot(x.y, x.z - 0.03) < 0.0336 and p.material_index in fix:
        p.material_index = fix[p.material_index]; k += 1
print("remapped", k)
