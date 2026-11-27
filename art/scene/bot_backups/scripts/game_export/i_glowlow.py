import bpy, math
o = bpy.data.objects["bot_game"]; me = o.data
pins = [(0.0, 0.042), (-0.0105, 0.024), (0.0105, 0.024)]
rig = bpy.data.objects["bot_rig"]
glow = []
for p in me.polygons:
    q = p.center  # mesh is in rig space; rig sits at the origin
    glow.append(q.x > -0.2425 and q.x < -0.2245 and min(math.hypot(q.y - y, q.z - z) for y, z in pins) < 0.005)
a = me.attributes.get("glow") or me.attributes.new("glow", "BOOLEAN", "FACE")
a.data.foreach_set("value", glow)
print("glow faces", sum(glow), "rig at", tuple(rig.location))
