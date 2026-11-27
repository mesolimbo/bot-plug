# ---- finish (reduced build): UVs, join into one skinned mesh named bot_new. The full-resolution bot_new is kept, hidden,
# as bot_new_full. bot_flap, the decals, the materials and the face textures already in the scene are left exactly as they are.
import os
old = bpy.data.objects.get("bot_new_full")
cur = bpy.data.objects.get("bot_new")
if old is None:
    old = cur
    old.name = "bot_new_full"
    old.data.name = "bot_new_full"
elif cur is not None:                      # a reduced bot_new from an earlier run
    me = cur.data
    bpy.data.objects.remove(cur, do_unlink=True)
    if me.users == 0:
        bpy.data.meshes.remove(me)
old.hide_render = True
drop("flap")                               # the dust cover is not rebuilt: bot_flap stays

parts = [o for o in coll().objects if o.type == "MESH" and not o.name.startswith(("tmp", "cut_", "cc_"))]
print("parts", len(parts), "verts", sum(len(o.data.vertices) for o in parts))


def edit_op(ob, fn):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    with bpy.context.temp_override(window=win, area=area, region=region, object=ob, active_object=ob, selected_objects=[ob], selected_editable_objects=[ob]):
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        fn()
        bpy.ops.object.mode_set(mode="OBJECT")


# --- UVs ---
for ob in parts:
    me = ob.data
    for mi, k in enumerate(ORDER):
        if mi < len(me.materials):
            me.materials[mi] = M[k]
    if ob.name == "screen":
        continue
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    if ob.name == "shell":
        # seams: every panel edge (lip and wall), plus two hidden cuts that split the big wrap-around panel at the bib ends
        bm = bmesh.new(); bm.from_mesh(me)
        pl = bm.faces.layers.int["panel"]
        A1, A2 = D(55.4, -10.6), D(37.0, -2.0)
        big = max(set(f[pl] for f in bm.faces), key=lambda k: sum(1 for f in bm.faces if f[pl] == k))
        for e in bm.edges:
            e.seam = (not e.smooth) or len(e.link_faces) != 2 or e.link_faces[0].material_index != e.link_faces[1].material_index
        for sgn in (1, -1):
            a1 = Vector((A1.x, sgn * A1.y, A1.z)); a2 = Vector((A2.x, sgn * A2.y, A2.z))
            nrm = a1.cross(a2).normalized(); L = (a2 - a1).length
            for e in bm.edges:
                if len(e.link_faces) != 2 or any(f[pl] != big or f.material_index != 0 for f in e.link_faces):
                    continue
                c0 = (e.link_faces[0].calc_center_median() - C).normalized(); c1 = (e.link_faces[1].calc_center_median() - C).normalized()
                mid = ((e.verts[0].co + e.verts[1].co) / 2 - C).normalized()
                if c0.dot(nrm) * c1.dot(nrm) < 0 and (mid - a1).length < L * 1.02 and (mid - a2).length < L * 1.02:
                    e.seam = True
        bm.to_mesh(me); bm.free()
        edit_op(ob, lambda: bpy.ops.uv.unwrap(method="ANGLE_BASED", margin=0.002))
    else:
        edit_op(ob, lambda: bpy.ops.uv.smart_project(angle_limit=math.radians(58), island_margin=0.002))
print("uv done %.1f" % (time.time() - T0))

# --- vertex groups, join ---
flap_src = bpy.data.objects.get("flap")
for ob in parts:
    vg = ob.vertex_groups.new(name=ob["bone"])
    vg.add(list(range(len(ob.data.vertices))), 1.0, "REPLACE")
body_parts = [o for o in parts if o is not flap_src]
main = body_parts[0]
for o in bpy.context.view_layer.objects:
    o.select_set(False)
for o in body_parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = main
with bpy.context.temp_override(window=win, area=area, region=region, object=main, active_object=main, selected_objects=body_parts, selected_editable_objects=body_parts):
    bpy.ops.object.join()
main.name = "bot_new"
main.data.name = "bot_new"
# keep the screen's planar UV, equalise and pack everything else into one atlas
me = main.data
si = ORDER.index("screen")
bm = bmesh.new(); bm.from_mesh(me)
uvl = bm.loops.layers.uv.active
scr_uv = {l.index: l[uvl].uv.copy() for f in bm.faces if f.material_index == si for l in f.loops}
bm.free()


def pack():
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(margin=0.0015)


edit_op(main, pack)
for li, uv in scr_uv.items():
    me.uv_layers.active.data[li].uv = uv
md = main.modifiers.new("Armature", "ARMATURE")
md.object = rig
main.parent = rig
main["bone"] = "rig"
main["reduced_from"] = "bot_new_full"
main.parent_type = old.parent_type
main.parent_bone = old.parent_bone
main.matrix_parent_inverse = old.matrix_parent_inverse.copy()
# into the collection the full one lives in; the build collection goes
for c in list(main.users_collection):
    c.objects.unlink(main)
for c in old.users_collection:
    c.objects.link(main)
c = bpy.data.collections.get(COLL)
assert c and not c.objects, [o.name for o in c.objects]
bpy.data.collections.remove(c)
old.hide_set(True)
bpy.context.view_layer.update()
print("joined: verts", len(me.vertices), "faces", len(me.polygons), "tris", sum(len(p.vertices) - 2 for p in me.polygons), "groups", [g.name for g in main.vertex_groups])
# every vertex must ride exactly one bone
bad = sum(1 for v in me.vertices if len(v.groups) != 1 or abs(v.groups[0].weight - 1.0) > 1e-6)
print("verts not weighted 100% to one bone:", bad)
print("final ok %.1f" % (time.time() - T0))
