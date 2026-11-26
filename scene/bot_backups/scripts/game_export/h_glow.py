# Inside of the three pin holes: their own glowing material (bot_glow), as on the old model.
import bpy, math
from mathutils import Vector
o = bpy.data.objects["bot_new"]; me = o.data
m = bpy.data.materials.get("bot_glow") or bpy.data.materials.new("bot_glow")
m.use_nodes = True
nt = m.node_tree; nt.nodes.clear()
out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled")
col = (1.0, 0.36, 0.03, 1)
b.inputs["Base Color"].default_value = col; b.inputs["Emission Color"].default_value = col
b.inputs["Emission Strength"].default_value = 3.0
nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])
m.diffuse_color = col
if m.name not in [x.name for x in me.materials if x]:
    me.materials.append(m)
gi = [x.name if x else "" for x in me.materials].index(m.name)
pi = [x.name if x else "" for x in me.materials].index("botn_plastic")
Z = 0.030
pins = [(0.0, Z + 0.012), (-0.0105, Z - 0.006), (0.0105, Z - 0.006)]
n = 0
for p in me.polygons:
    if p.material_index not in (pi, gi):
        continue
    q = o.matrix_world @ p.center
    inside = q.x > -0.2425 and min(math.hypot(q.y - y, q.z - z) for y, z in pins) < 0.005
    if inside:
        p.material_index = gi; n += 1
print("glow faces", n, "slot", gi)
