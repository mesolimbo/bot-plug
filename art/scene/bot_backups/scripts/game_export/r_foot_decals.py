# Foot slot decals: a tidy take on the old model's foot slots, laid on each foot's sloped top-front face
# 0.6 mm above the game mesh and weighted to that foot's bone. Run after j_decals.py (which rebuilds only
# the bot_decal_* meshes made from decal_* objects, so it would leave these alone but not recreate them).
import os

import bmesh
import bpy
from mathutils import Vector

SCENE_DIR = os.path.dirname(bpy.data.filepath)
IMG = os.path.join(SCENE_DIR, "bot_decal_foot_slot.png")
WIDTH, HEIGHT = 0.072, 0.054      # metres; the image is 4:3 (slot plus its U-shaped groove)
SLOT_UP = 0.0025                  # the decal centre sits this far up the slope from the slot centre
UP = 0.42                         # slot centre from the toe end (0) to the ankle end (1) of the slope; its groove reaches the top edge
LIFT = 0.0006

rig = bpy.data.objects["bot_rig"]
rig.data.pose_position = "REST"
bpy.context.view_layer.update()
low = bpy.data.objects["bot_game"]
me, M = low.data, low.matrix_world
gc = bpy.data.collections["bot_game"]

for o in list(gc.objects):
    if o.name.startswith("bot_decal_foot"):
        m = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.meshes.remove(m)

mat = bpy.data.materials.get("botn_decal_foot") or bpy.data.materials.new("botn_decal_foot")
mat.use_nodes = True
nt = mat.node_tree
nt.nodes.clear()
out = nt.nodes.new("ShaderNodeOutputMaterial")
bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
tex = nt.nodes.new("ShaderNodeTexImage")
img = bpy.data.images.get("bot_decal_foot_slot.png") or bpy.data.images.load(IMG)
img.name = "bot_decal_foot_slot.png"
tex.image = img
tex.extension = "CLIP"
nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
bsdf.inputs["Roughness"].default_value = 0.55
nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
mat.surface_render_method = "BLENDED"

for side in ("L", "R"):
    bone = "foot." + side
    gi = low.vertex_groups[bone].index
    feet = {v.index for v in me.vertices if any(g.group == gi and g.weight > 0.5 for g in v.groups)}
    # The sloped face: forward-and-up normals ahead of the ankle.
    faces = []
    for p in me.polygons:
        if not all(i in feet for i in p.vertices):
            continue
        n = (M.to_3x3() @ p.normal).normalized()
        c = M @ p.center
        if n.x > 0.45 and n.z > 0.65 and abs(n.y) < 0.15 and c.x > 0.0:
            faces.append((p, n, c))
    area = sum(p.area for p, _, _ in faces)
    normal = sum((n * p.area for p, n, _ in faces), Vector()).normalized()
    centre = sum((c * p.area for p, _, c in faces), Vector()) / area
    across = Vector((0, 1, 0))
    up = normal.cross(across).normalized()          # along the slope towards the ankle
    if up.z < 0:
        up = -up
    across = up.cross(normal).normalized()          # image right
    pts = [M @ me.vertices[i].co for p, _, _ in faces for i in p.vertices]
    s = [(q - centre).dot(up) for q in pts]
    t = [(q - centre).dot(across) for q in pts]
    mid = centre + up * (min(s) + (max(s) - min(s)) * UP) + across * ((min(t) + max(t)) / 2)
    # A small grid dropped onto the foot's actual surface (the averaged plane can sit inside it), then lifted.
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    NX, NY = 12, 9
    grid = []
    for j in range(NY + 1):
        row = []
        for i in range(NX + 1):
            p = mid + across * ((i / NX - 0.5) * WIDTH) + up * ((j / NY - 0.5) * HEIGHT + SLOT_UP)
            hit, loc, _, _ = low.ray_cast(M.inverted() @ (p + normal * 0.04), M.to_3x3().inverted() @ -normal, distance=0.08)
            q = (M @ loc if hit else p) + normal * LIFT
            row.append((bm.verts.new(q), (i / NX, j / NY)))
        grid.append(row)
    for j in range(NY):
        for i in range(NX):
            quad = [grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]]
            f = bm.faces.new([v for v, _ in quad])
            for loop, (_, uv) in zip(f.loops, quad):
                loop[uvl].uv = uv
    bm.normal_update()
    if sum(f.normal.dot(normal) for f in bm.faces) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    name = "bot_decal_foot_" + side
    dm = bpy.data.meshes.new(name)
    bm.to_mesh(dm)
    bm.free()
    dm.materials.append(mat)
    ob = bpy.data.objects.new(name, dm)
    gc.objects.link(ob)
    vg = ob.vertex_groups.new(name=bone)
    vg.add(range(len(dm.vertices)), 1.0, "REPLACE")
    ob.parent = rig
    am = ob.modifiers.new("Armature", "ARMATURE")
    am.object = rig
    ob.hide_render = True  # keep it out of the paint bakes
    print(name, "centre", [round(x, 4) for x in sum((v.co for v in dm.vertices), Vector()) / len(dm.vertices)], "normal", [round(x, 3) for x in normal],
          "slope %.0f x %.0f mm" % ((max(s) - min(s)) * 1000, (max(t) - min(t)) * 1000))
