import bpy
for o in bpy.data.objects:
    if o.name.startswith("bot_decal"):
        o.hide_render = True
print("hidden", [o.name for o in bpy.data.objects if o.name.startswith("bot_decal")])
