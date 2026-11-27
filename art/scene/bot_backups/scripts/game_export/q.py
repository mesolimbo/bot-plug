import bpy
o = bpy.data.objects["bot"]; print("old tris", sum(len(p.vertices) - 2 for p in o.data.polygons))
