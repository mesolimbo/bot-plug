# Check renders: seam junction close-ups, socket (open, closed, plug seated), general previews.
import json


def shoot_dir(path, d, ortho, dist=2.0, r=0.27):
    cam = get_cam()
    aim(cam, C + d * dist, C + d * r, ortho, "Y")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


names = [o.name for o in bpy.data.collections["botn"].all_objects]
hidden = {o.name: o.hide_render for o in bpy.data.objects}
only_render(names)
setup_wb(420, False, "MATERIAL", "STUDIO")
jn = []
for i, (label, d) in enumerate(JUNCTION_PTS.items()):
    shoot_dir(VD + "\\junc_%02d.png" % i, d, 0.075)
    jn.append(label)
json.dump(jn, open(VD + "\\junc_names.json", "w"))
for o in bpy.data.objects:
    o.hide_render = hidden.get(o.name, o.hide_render)

SK = {"k_back": ((-2, 0, 0.03), (0, 0, 0.03), 0.3), "k_backq": ((-2, 1.0, -0.6), (-0.2, 0, 0.0), 0.3), "k_side": ((-0.2, 2, 0.0), (-0.2, 0, 0.0), 0.3),
      "k_close": ((-2, 0, 0.03), (0, 0, 0.03), 0.12), "k_closeq": ((-2, 0.9, 0.9), (-0.25, 0, 0.03), 0.14)}
new_shots(SK, 1000, prefix="n_")
fl = bpy.data.objects["flap"]
rot = fl.rotation_euler.y
fl.rotation_euler.y = 0.0
bpy.context.view_layer.update()
new_shots({k: SK[k] for k in ("k_back", "k_backq", "k_side")}, 1000, prefix="nc_")
fl.rotation_euler.y = rot
bpy.context.view_layer.update()

# plug seated (temporary copy from scene/plug.blend, removed afterwards)
tp = bpy.data.collections.get("tmp_plug")
if tp:
    plug = bpy.data.objects.get("plug")
    plug.location = (-0.245, 0.0, 0.030)
    plug.rotation_euler = (0, 0, math.pi)
    bpy.context.view_layer.update()
    pnames = [o.name for o in tp.objects if o.parent is plug]
    # numeric clearance: pins against the receptacle
    cl = bpy.data.objects["socket_clover"]
    bmc = bmesh.new(); bmc.from_mesh(cl.data); bvc = BVHTree.FromBMesh(bmc)
    for o in tp.objects:
        if o.parent is plug and o.type == "MESH" and len(o.data.vertices) == 24:
            vs = [o.matrix_world @ v.co for v in o.data.vertices]
            dmin = min(bvc.find_nearest(v)[3] for v in vs)
            cy = sum(v.y for v in vs) / len(vs); cz = sum(v.z for v in vs) / len(vs)
            print("pin %s centre y %.4f z %.4f  x %.4f..%.4f  min clearance to receptacle %.2f mm" % (o.name, cy, cz, min(v.x for v in vs), max(v.x for v in vs), dmin * 1000))
    bmc.free()
    hidden = {o.name: o.hide_render for o in bpy.data.objects}
    only_render(names + pnames)
    setup_wb(1000, False, "MATERIAL", "STUDIO")
    for nm, (loc, tgt, ortho) in {"k_plug": ((-2, 0.9, 0.9), (-0.28, 0, 0.03), 0.22), "k_plugside": ((-0.25, 2, 0.03), (-0.27, 0, 0.03), 0.22)}.items():
        shoot(VD + "\\n_" + nm + ".png", loc, tgt, ortho)
    for o in bpy.data.objects:
        o.hide_render = hidden.get(o.name, o.hide_render)
    for o in list(tp.objects):
        me = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if me and me.users == 0:
            bpy.data.meshes.remove(me)
    bpy.data.collections.remove(tp)
    for m in list(bpy.data.materials):
        if m.users == 0 and not m.name.startswith(("botn_", "bot_", "view_")):
            bpy.data.materials.remove(m)
    print("temporary plug removed")
new_shots(STD, 800, prefix="n_")
print("checks done")
