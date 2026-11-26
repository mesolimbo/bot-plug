import bpy
gc = bpy.data.collections["bot_game"]; print(len(gc.objects), [o.name for o in list(gc.objects)[:5]])
