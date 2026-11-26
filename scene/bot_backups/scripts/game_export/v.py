import bpy
me = bpy.data.objects["bot_game"].data
print("changed", me.validate(verbose=True), len(me.vertices), len(me.polygons))
