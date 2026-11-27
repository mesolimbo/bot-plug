# Split the full-detail bot (with dust cover) into loose parts in collection bot_qr, each tagged with its bone and size.
import bpy, bmesh
win = bpy.context.window_manager.windows[0]
area = next(a for a in win.screen.areas if a.type == "VIEW_3D")
region = next(r for r in area.regions if r.type == "WINDOW")
rig = bpy.data.objects["bot_rig"]; rig.data.pose_position = "REST"
bpy.context.view_layer.update()
qc = bpy.data.collections.get("bot_qr") or bpy.data.collections.new("bot_qr")
if qc.name not in bpy.context.scene.collection.children:
    bpy.context.scene.collection.children.link(qc)
for o in list(qc.objects):
    me = o.data; bpy.data.objects.remove(o, do_unlink=True); bpy.data.meshes.remove(me)
def copy_world(src, name):
    me = src.data.copy(); me.name = name; me.transform(src.matrix_world)
    o = bpy.data.objects.new(name, me); qc.objects.link(o); return o
def ctx(objs, active):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active
    return bpy.context.temp_override(window=win, area=area, region=region, object=active, active_object=active,
                                     selected_objects=objs, selected_editable_objects=objs)
full = copy_world(bpy.data.objects["bot_new"], "qp")
flap = copy_world(bpy.data.objects["bot_flap"], "tmp_flap")
vg = flap.vertex_groups.get("body") or flap.vertex_groups.new(name="body")
vg.add(range(len(flap.data.vertices)), 1.0, "REPLACE")
with ctx([full, flap], full):
    bpy.ops.object.join()
with ctx([full], full):
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="LOOSE"); bpy.ops.object.mode_set(mode="OBJECT")
parts = sorted(qc.objects, key=lambda o: -len(o.data.polygons))
for i, o in enumerate(parts):
    me = o.data
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    w = {}
    for v in me.vertices:
        for g in v.groups:
            if g.weight > 0.5:
                n = o.vertex_groups[g.group].name; w[n] = w.get(n, 0) + 1
    o.name = me.name = "qp_%03d" % i
    o["tris"] = tris
    o["bone"] = max(w, key=w.get) if w else "body"
    o["bones"] = len(w)
    o.hide_set(True)
multi = [o.name for o in parts if o["bones"] > 1]
print("parts", len(parts), "multi-bone parts", multi, "big", sum(1 for o in parts if o["tris"] >= 500))
