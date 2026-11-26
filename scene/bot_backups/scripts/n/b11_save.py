# ---- tidy and save scene/bot.blend (the original tripo-out file is never touched) ----------------------------
OUT = r"C:\Users\mesol\OneDrive\Documents\Art\2026\Alan's Bot Plugs\scene\bot.blend"
assert bpy.data.filepath.lower() == OUT.lower(), bpy.data.filepath
for nm in ("old_legL", "old_thighL", "old_shinL", "old_footL", "old_body", "b2_cam", "proj_cam"):
    o = bpy.data.objects.get(nm)
    if o:
        d = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if d and d.users == 0:
            (bpy.data.meshes if isinstance(d, bpy.types.Mesh) else bpy.data.cameras).remove(d)
for nm in ("bot", "bot_src"):
    o = bpy.data.objects.get(nm)
    if o:
        o.hide_set(True)
        o.hide_render = True
for o in bpy.data.collections["botn"].all_objects:
    o.hide_render = False
    o.hide_set(False)
rig = bpy.data.objects["bot_rig"]
rig.data.pose_position = "POSE"
scene.frame_set(1)
scene.render.film_transparent = False
bpy.ops.wm.save_mainfile()
print("saved", bpy.data.filepath, [o.name for o in bpy.data.collections["botn"].all_objects])
