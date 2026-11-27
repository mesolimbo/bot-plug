# Render old (bot_new[_full] + bot_flap) and new (botr collection or NEW_NAMES) from the same cameras. Workbench, material colours.
import bpy, math
from mathutils import Vector
OUT = r"C:\Users\mesol\AppData\Local\Temp\claude\3fec41d04d410712\f1237eee-dce1-4b40-88e6-7a7228eb5a6b\scratchpad\cmp"
VIEWS_ALL = {
 "front": ((1, 0, 0.12), (0, 0, 0.03), 0.78), "left": ((0.35, 1, 0.15), (0, 0, 0.03), 0.78), "right": ((0.35, -1, 0.15), (0, 0, 0.03), 0.78),
 "back": ((-1, 0.15, 0.12), (0, 0, 0.03), 0.78), "top": ((0.25, 0.1, 1), (0, 0, 0.03), 0.78),
 "vent_front": ((1, 0.25, 1.1), (0.12, 0.0, 0.27), 0.26), "vent_rear": ((-1, 0.3, 1.2), (-0.13, 0.0, 0.27), 0.26), "vent_side": ((0.2, 1, 1.0), (0.0, 0.12, 0.27), 0.26),
 "socket": ((-1, 0.0, 0.0), (-0.24, 0, 0.03), 0.12), "socket_q": ((-1, 0.45, 0.35), (-0.24, 0, 0.045), 0.2),
 "leg_joint": ((0.5, 1, 0.1), (0.02, 0.1, -0.27), 0.3), "hip": ((0.3, 1, -0.35), (0.0, 0.1, -0.1), 0.3),
 "face": ((1, 0.3, 0.1), (0.24, 0, 0.073), 0.4), "under": ((0.2, 0.1, -1), (0, 0, 0.0), 0.62), "rear_low": ((-1, 0.2, -0.6), (-0.2, 0, -0.06), 0.3),
 "cheek": ((-0.7, 1, 0.1), (-0.15, 0.2, 0.05), 0.34), "brow": ((1, 0.5, 0.5), (0.2, 0.1, 0.22), 0.26),
}
VIEWS = globals().get("VIEWS", None) or list(VIEWS_ALL)
RES = globals().get("RES", 1000)
FLAT = globals().get("FLAT", False)
OLD = globals().get("OLD_NAMES", None) or ["bot_new_full" if "bot_new_full" in bpy.data.objects else "bot_new", "bot_flap"]
NEW = globals().get("NEW_NAMES", None) or ([o.name for o in bpy.data.collections["botr"].objects if o.type == "MESH"] if "botr" in bpy.data.collections else ["bot_new", "bot_flap"])
SETS = globals().get("SETS", None) or {"old": OLD, "new": NEW}
sc = bpy.context.scene
rig = bpy.data.objects["bot_rig"]
pp = rig.data.pose_position
rig.data.pose_position = globals().get("POSE", "REST")
keep = {o.name: (o.hide_render, o.hide_get()) for o in bpy.data.objects}
sh = sc.display.shading
old = dict(engine=sc.render.engine, cam=sc.camera, rx=sc.render.resolution_x, ry=sc.render.resolution_y, ft=sc.render.film_transparent, light=sh.light, ct=sh.color_type,
           cav=sh.show_cavity, cavt=sh.cavity_type, outl=sh.show_object_outline, vt=sc.view_settings.view_transform, ff=sc.render.image_settings.file_format, fp=sc.render.filepath,
           pct=sc.render.resolution_percentage, shadow=sh.show_shadows, cm=sc.render.image_settings.color_mode)
sc.render.engine = "BLENDER_WORKBENCH"
sh.light = "STUDIO"; sh.color_type = "MATERIAL"; sh.show_cavity = True; sh.cavity_type = "BOTH"; sh.show_object_outline = False; sh.show_shadows = False
sc.render.resolution_x = sc.render.resolution_y = RES; sc.render.resolution_percentage = 100; sc.render.film_transparent = False
sc.view_settings.view_transform = "Standard"; sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGB"
cd = bpy.data.cameras.get("cmp_cam") or bpy.data.cameras.new("cmp_cam")
cam = bpy.data.objects.get("cmp_cam") or bpy.data.objects.new("cmp_cam", cd)
if cam.name not in sc.collection.objects: sc.collection.objects.link(cam)
cd.type = "ORTHO"; cd.clip_start = 0.01; sc.camera = cam
flat_restore = []
try:
    for tag, names in SETS.items():
        names = set(names)
        for o in bpy.data.objects:
            if o.type in ("MESH", "CURVE"):
                o.hide_render = o.name not in names
                if o.name in names: o.hide_set(False)
        if FLAT:
            for nm in names:
                me = bpy.data.objects[nm].data
                s = [p.use_smooth for p in me.polygons]; flat_restore.append((me, s))
                me.polygons.foreach_set("use_smooth", [False] * len(s)); me.update()
        for v in VIEWS:
            d, tgt, ortho = VIEWS_ALL[v] if isinstance(v, str) else v[1:]
            vn = v if isinstance(v, str) else v[0]
            d = Vector(d).normalized(); cd.ortho_scale = ortho
            cam.location = Vector(tgt) + d * 3
            cam.rotation_euler = (-d).to_track_quat("-Z", "Y" if abs(d.z) < 0.99 else "X").to_euler()
            sc.render.filepath = OUT + "\\" + tag + "_" + vn + ("_flat" if FLAT else "") + ".png"
            bpy.ops.render.render(write_still=True)
        for me, s in flat_restore:
            me.polygons.foreach_set("use_smooth", s); me.update()
        flat_restore = []
finally:
    for o in bpy.data.objects:
        if o.name in keep:
            o.hide_render = keep[o.name][0]; o.hide_set(keep[o.name][1])
    sc.render.engine = old["engine"]; sc.camera = old["cam"]; sc.render.resolution_x = old["rx"]; sc.render.resolution_y = old["ry"]; sc.render.film_transparent = old["ft"]
    sh.light = old["light"]; sh.color_type = old["ct"]; sh.show_cavity = old["cav"]; sh.cavity_type = old["cavt"]; sh.show_object_outline = old["outl"]; sh.show_shadows = old["shadow"]
    sc.view_settings.view_transform = old["vt"]; sc.render.image_settings.file_format = old["ff"]; sc.render.filepath = old["fp"]; sc.render.resolution_percentage = old["pct"]
    sc.render.image_settings.color_mode = old["cm"]
    rig.data.pose_position = pp
    bpy.data.objects.remove(cam); bpy.data.cameras.remove(cd)
print("views ok", list(SETS), len(VIEWS))
