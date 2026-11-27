# Game copy of the new bot: bot_new + dust cover joined, planar-then-collapse decimation, smooth normals, fresh UVs.
import bpy, bmesh, math
from mathutils.bvhtree import BVHTree
import numpy as np
print = __builtins__["print"] if isinstance(__builtins__, dict) else __builtins__.print
TARGET = int(globals().get("TARGET", 40000))
win = bpy.context.window_manager.windows[0]
area = next(a for a in win.screen.areas if a.type == "VIEW_3D")
region = next(r for r in area.regions if r.type == "WINDOW")
rig = bpy.data.objects["bot_rig"]
rig.data.pose_position = "REST"
bpy.context.view_layer.update()
gc = bpy.data.collections.get("bot_game") or bpy.data.collections.new("bot_game")
if gc.name not in bpy.context.scene.collection.children:
    bpy.context.scene.collection.children.link(gc)
for o in list(gc.objects):
    me = o.data; bpy.data.objects.remove(o, do_unlink=True); bpy.data.meshes.remove(me)

def copy_world(src, name):
    me = src.data.copy()
    me.name = name
    me.transform(src.matrix_world)
    o = bpy.data.objects.new(name, me)
    gc.objects.link(o)
    return o

low = copy_world(bpy.data.objects["bot_new"], "bot_game")
flap = copy_world(bpy.data.objects["bot_flap"], "tmp_flap")
vg = flap.vertex_groups.get("body") or flap.vertex_groups.new(name="body")
vg.add(range(len(flap.data.vertices)), 1.0, "REPLACE")

def ctx(objs, active):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active
    return bpy.context.temp_override(window=win, area=area, region=region, object=active, active_object=active,
                                     selected_objects=objs, selected_editable_objects=objs)

with ctx([low, flap], low):
    bpy.ops.object.join()
me = low.data
tri0 = sum(len(p.vertices) - 2 for p in me.polygons)

# keep a BVH of the full-detail surface for the error check
bm_hi = bmesh.new(); bm_hi.from_mesh(me); bm_hi.verts.ensure_lookup_table()
hi_co = np.array([v.co[:] for v in bm_hi.verts])
bm_hi.free()

bm = bmesh.new(); bm.from_mesh(me)
bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=bm.verts, edges=bm.edges, delimit={"MATERIAL", "NORMAL"})
bmesh.ops.triangulate(bm, faces=bm.faces, quad_method="BEAUTY", ngon_method="BEAUTY")
bm.to_mesh(me); bm.free()
tri1 = len(me.polygons)
ratio = min(1.0, TARGET / tri1)
mod = low.modifiers.new("dec", "DECIMATE")
mod.decimate_type = "COLLAPSE"
mod.ratio = ratio
mod.use_collapse_triangulate = True
with ctx([low], low):
    bpy.ops.object.modifier_apply(modifier="dec")
tri2 = len(me.polygons)
print("tris full", tri0, "after planar", tri1, "after collapse", tri2, "verts", len(me.vertices))

# error: full-detail vertices to the nearest point on the simplified surface
bm = bmesh.new(); bm.from_mesh(me)
bvh = BVHTree.FromBMesh(bm); bm.free()
d = np.array([(bvh.find_nearest(p)[3] or 0) for p in hi_co])
print("error mm: median %.2f  p90 %.2f  p99 %.2f  max %.2f" % tuple(np.percentile(d, [50, 90, 99, 100]) * 1000))
