# Decals as their own skinned meshes in the game file (full-resolution images), seated 0.6 mm above the simplified surface.
import bpy, bmesh
from mathutils.bvhtree import BVHTree
win = bpy.context.window_manager.windows[0]
area = next(a for a in win.screen.areas if a.type == "VIEW_3D")
region = next(r for r in area.regions if r.type == "WINDOW")
rig = bpy.data.objects["bot_rig"]; rig.data.pose_position = "REST"
bpy.context.view_layer.update()
gc = bpy.data.collections["bot_game"]
for o in list(gc.objects):
    if o.name.startswith("bot_decal"):
        me = o.data; bpy.data.objects.remove(o, do_unlink=True); bpy.data.meshes.remove(me)
low = bpy.data.objects["bot_game"]
bm = bmesh.new(); bm.from_mesh(low.data); bvh = BVHTree.FromBMesh(bm); bm.free()
groups = {}
for o in bpy.data.objects:
    if o.name.startswith("decal_"):
        groups.setdefault(o.data.materials[0].name, []).append(o)
for mat, objs in groups.items():
    bm = bmesh.new()
    for o in objs:
        tmp = o.data.copy(); tmp.transform(o.matrix_world)
        bm.from_mesh(tmp); bpy.data.meshes.remove(tmp)
    moved = 0
    for v in bm.verts:
        loc, n, i, d = bvh.find_nearest(v.co)
        if loc is not None and d < 0.004:
            side = 1 if (v.co - loc).dot(n) >= 0 else -1
            v.co = loc + n * 0.0006 if side > 0 or d < 0.002 else v.co
            moved += 1
    name = "bot_decal_" + mat.split("decal_")[-1]
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.materials.append(bpy.data.materials[mat])
    ob = bpy.data.objects.new(name, me); gc.objects.link(ob)
    vg = ob.vertex_groups.new(name="body"); vg.add(range(len(me.vertices)), 1.0, "REPLACE")
    ob.parent = rig
    am = ob.modifiers.new("Armature", "ARMATURE"); am.object = rig
    ob.hide_render = True  # keep them out of the paint bakes
    print(name, len(me.vertices), "snapped", moved)
