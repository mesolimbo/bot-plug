import bpy
o = bpy.data.objects["bot_game"]
print("groups", [g.name for g in o.vertex_groups], "weighted verts", sum(1 for v in o.data.vertices if v.groups), len(o.data.vertices), "parent", o.parent, [m.type for m in o.modifiers])
