# Import a GLB, render it flat-lit with its own textures from fixed cameras, then remove everything the import added.
import bpy
from mathutils import Vector
S = r"C:\Users\mesol\AppData\Local\Temp\claude\3fec41d04d410712\f1237eee-dce1-4b40-88e6-7a7228eb5a6b\scratchpad"
VIEWS = {"front": ((1, 0, 0.12), (0, 0, 0.03), 0.78), "left": ((0.35, 1, 0.15), (0, 0, 0.03), 0.78), "right": ((0.35, -1, 0.15), (0, 0, 0.03), 0.78),
         "back": ((-1, 0.15, 0.12), (0, 0, 0.03), 0.78), "top": ((0.25, 0.1, 1), (0, 0, 0.03), 0.78),
         "vent_front": ((1, 0.25, 1.1), (0.12, 0.0, 0.27), 0.26), "vent_rear": ((-1, 0.3, 1.2), (-0.13, 0.0, 0.27), 0.26),
         "socket": ((-1, 0.0, 0.0), (-0.24, 0, 0.03), 0.12), "socket_q": ((-1, 0.45, 0.35), (-0.24, 0, 0.045), 0.2),
         "leg_joint": ((0.5, 1, 0.1), (0.02, 0.1, -0.27), 0.3), "face": ((1, 0.3, 0.1), (0.24, 0, 0.073), 0.4), "cheek": ((-0.7, 1, 0.1), (-0.15, 0.2, 0.05), 0.34)}
win = bpy.context.window_manager.windows[0]
area = next(a for a in win.screen.areas if a.type == "VIEW_3D")
region = next(r for r in area.regions if r.type == "WINDOW")
sc = bpy.context.scene
def snap():
    return {k: set(getattr(bpy.data, k)) for k in ("objects", "meshes", "armatures", "materials", "images", "actions", "textures", "collections", "cameras")}
sh = sc.display.shading
old = dict(engine=sc.render.engine, cam=sc.camera, rx=sc.render.resolution_x, ry=sc.render.resolution_y, ft=sc.render.film_transparent, light=sh.light, ct=sh.color_type,
           vt=sc.view_settings.view_transform, ff=sc.render.image_settings.file_format, fp=sc.render.filepath, pct=sc.render.resolution_percentage, fr=sc.frame_current,
           act=bpy.context.view_layer.objects.active, cav=sh.show_cavity)
keep = {o.name: (o.hide_render, o.hide_get()) for o in bpy.data.objects}
sel = [o for o in bpy.context.view_layer.objects if o.select_get()]
for tag, path in GLBS.items():
    before = snap()
    with bpy.context.temp_override(window=win, area=area, region=region):
        bpy.ops.import_scene.gltf(filepath=path)
    new = {k: set(getattr(bpy.data, k)) - before[k] for k in before}
    try:
        for o in bpy.data.objects:
            if o.type in ("MESH", "CURVE"):
                o.hide_render = o not in new["objects"]
        for a in new["armatures"]:
            a.pose_position = "REST"
        bpy.context.view_layer.update()
        sc.render.engine = "BLENDER_WORKBENCH"; sh.light = "FLAT"; sh.color_type = "TEXTURE"; sh.show_cavity = False
        sc.render.resolution_x = sc.render.resolution_y = RES; sc.render.resolution_percentage = 100
        sc.view_settings.view_transform = "Standard"; sc.render.image_settings.file_format = "PNG"
        cd = bpy.data.cameras.new("glb_cam"); cam = bpy.data.objects.new("glb_cam", cd); sc.collection.objects.link(cam)
        cd.type = "ORTHO"; cd.clip_start = 0.01; sc.camera = cam
        for v, (d, tgt, ortho) in VIEWS.items():
            d = Vector(d).normalized(); cd.ortho_scale = ortho
            cam.location = Vector(tgt) + d * 3; cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
            sc.render.filepath = S + "\cmp\glb" + tag + "_" + v + ".png"
            bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(cam); bpy.data.cameras.remove(cd)
        print(tag, "meshes", sorted((o.name, sum(len(p.vertices) - 2 for p in o.data.polygons)) for o in new["objects"] if o.type == "MESH"))
    finally:
        for o in list(new["objects"]): bpy.data.objects.remove(o, do_unlink=True)
        for k in ("meshes", "armatures", "materials", "textures", "images", "actions", "collections"):
            for d in list(new[k]):
                try: getattr(bpy.data, k).remove(d)
                except Exception as e: print("cleanup", k, e)
for o in bpy.data.objects:
    if o.name in keep:
        o.hide_render = keep[o.name][0]; o.hide_set(keep[o.name][1])
sc.render.engine = old["engine"]; sc.camera = old["cam"]; sc.render.resolution_x = old["rx"]; sc.render.resolution_y = old["ry"]; sc.render.film_transparent = old["ft"]
sh.light = old["light"]; sh.color_type = old["ct"]; sh.show_cavity = old["cav"]; sc.view_settings.view_transform = old["vt"]; sc.render.image_settings.file_format = old["ff"]
sc.render.filepath = old["fp"]; sc.render.resolution_percentage = old["pct"]; sc.frame_set(old["fr"])
for o in bpy.context.view_layer.objects: o.select_set(o in sel)
bpy.context.view_layer.objects.active = old["act"]
print("glb views ok")
