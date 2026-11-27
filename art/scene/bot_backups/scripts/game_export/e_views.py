import bpy, math
from mathutils import Vector
G = "C:/Users/mesol/AppData/Local/Temp/claude/3fec41d04d410712/f1237eee-dce1-4b40-88e6-7a7228eb5a6b/scratchpad/g"
sc = bpy.context.scene
rig = bpy.data.objects["bot_rig"]; rig.data.pose_position = "REST"
low = bpy.data.objects["bot_game"]
keep = {o.name: o.hide_render for o in bpy.data.objects}
for o in bpy.data.objects:
    if o.type in ("MESH", "CURVE"):
        o.hide_render = o is not low
low.hide_set(False)
old = dict(engine=sc.render.engine, cam=sc.camera, rx=sc.render.resolution_x, ry=sc.render.resolution_y, ft=sc.render.film_transparent)
sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading; sh.light = "FLAT"; sh.color_type = "TEXTURE"
sc.render.resolution_x = sc.render.resolution_y = 900
sc.view_settings.view_transform = "Standard"
sc.render.image_settings.file_format = "PNG"
cd = bpy.data.cameras.get("g_cam") or bpy.data.cameras.new("g_cam")
cam = bpy.data.objects.get("g_cam") or bpy.data.objects.new("g_cam", cd)
if cam.name not in sc.collection.objects: sc.collection.objects.link(cam)
cd.type = "ORTHO"; cd.ortho_scale = 0.78
sc.camera = cam
tgt = Vector((0, 0, 0.03))
for name, d in {"front": (1, 0, 0.12), "left": (0.35, 1, 0.15), "back": (-1, 0.15, 0.12), "right": (0.35, -1, 0.15), "top": (0.25, 0.1, 1)}.items():
    v = Vector(d).normalized()
    cam.location = tgt + v * 3
    cam.rotation_euler = (-v).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = G + "/view_" + name + ".png"
    bpy.ops.render.render(write_still=True)
for o in bpy.data.objects:
    if o.name in keep: o.hide_render = keep[o.name]
sc.render.engine = old["engine"]; sc.camera = old["cam"]; sc.render.resolution_x = old["rx"]; sc.render.resolution_y = old["ry"]
low.hide_set(True); rig.data.pose_position = "POSE"
print("views ok")
