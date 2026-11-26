# Per-part simplification: each loose part gets the lowest ratio whose two-way error stays under TOL.
import bpy, bmesh, math
from mathutils.bvhtree import BVHTree
import numpy as np
TOL = float(globals().get("TOL", 0.0006))
win = bpy.context.window_manager.windows[0]
area = next(a for a in win.screen.areas if a.type == "VIEW_3D")
region = next(r for r in area.regions if r.type == "WINDOW")
rig = bpy.data.objects["bot_rig"]; rig.data.pose_position = "REST"
bpy.context.view_layer.update()
gc = bpy.data.collections["bot_game"]
old_mat = bpy.data.materials.get("bot_game_mat")
for o in list(gc.objects):
    me = o.data; bpy.data.objects.remove(o, do_unlink=True); bpy.data.meshes.remove(me)

def copy_world(src, name):
    me = src.data.copy(); me.name = name; me.transform(src.matrix_world)
    o = bpy.data.objects.new(name, me); gc.objects.link(o); return o

def ctx(objs, active):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active
    return bpy.context.temp_override(window=win, area=area, region=region, object=active, active_object=active,
                                     selected_objects=objs, selected_editable_objects=objs)

full = copy_world(bpy.data.objects["bot_new"], "bot_game")
flap = copy_world(bpy.data.objects["bot_flap"], "tmp_flap")
vg = flap.vertex_groups.get("body") or flap.vertex_groups.new(name="body")
vg.add(range(len(flap.data.vertices)), 1.0, "REPLACE")
with ctx([full, flap], full):
    bpy.ops.object.join()
with ctx([full], full):
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="LOOSE"); bpy.ops.object.mode_set(mode="OBJECT")
parts = list(gc.objects)

def tris(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)

def simplify(bm_src, ratio):
    bm = bm_src.copy()  # no flat-face merging: it can leave faces spanning a hole
    bmesh.ops.triangulate(bm, faces=bm.faces)
    return bm

def err(bm_a, bvh_b):
    pts = [v.co for v in bm_a.verts] + [f.calc_center_median() for f in bm_a.faces]
    pts += [(e.verts[0].co + e.verts[1].co) / 2 for e in bm_a.edges]
    return max((bvh_b.find_nearest(p)[3] or 0) for p in pts)

tot0 = tot1 = 0
kept = 0
for o in parts:
    me = o.data
    t0 = tris(me); tot0 += t0
    bm_hi = bmesh.new(); bm_hi.from_mesh(me)
    bvh_hi = BVHTree.FromBMesh(bm_hi)
    bm_p = simplify(bm_hi, 1)
    base = bmesh.new(); base = bm_p  # planar result is exact enough to start from
    me_p = me.copy(); bm_p.to_mesh(me_p)  # a copy keeps the vertex group names
    best = me_p
    tp = len(me_p.polygons)
    for ratio in globals().get("RATIOS", (0.05, 0.08, 0.12, 0.18, 0.25, 0.4, 0.6, 0.8)):
        if tp * ratio < 8:
            continue
        o.data = me_p.copy()
        m = o.modifiers.new("dec", "DECIMATE"); m.decimate_type = "COLLAPSE"; m.ratio = ratio; m.use_collapse_triangulate = True
        with ctx([o], o):
            bpy.ops.object.modifier_apply(modifier="dec")
        bm_l = bmesh.new(); bm_l.from_mesh(o.data); bvh_l = BVHTree.FromBMesh(bm_l)
        e = max(err(bm_hi, bvh_l), err(bm_l, bvh_hi))
        bm_l.free()
        if e <= TOL:
            best = o.data
            break
        rej = o.data
        o.data = me_p
        bpy.data.meshes.remove(rej)
    else:
        kept += 1
    o.data = best
    if best is not me_p:
        bpy.data.meshes.remove(me_p)
    bm_hi.free()
    tot1 += tris(o.data)
    if me.users == 0:
        bpy.data.meshes.remove(me)
first = parts[0]
with ctx(parts, first):
    bpy.ops.object.join()
first.name = "bot_game"; first.data.name = "bot_game"
me = first.data
me.validate()
if False:  # materials stay per part; b_uv reads them
    me.materials.clear(); me.materials.append(old_mat)
print("parts", len(parts), "tris", tot0, "->", tot1, "parts left at planar-only", kept)
