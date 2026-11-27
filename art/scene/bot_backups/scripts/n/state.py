import bpy
print(bpy.data.filepath, bpy.app.version_string)
for c in bpy.data.collections:
    print("coll", c.name, len(c.objects))
for o in bpy.data.objects:
    if o.users_collection and o.users_collection[0].name != "bot2":
        print(o.name, o.type, [c.name for c in o.users_collection], o.hide_get() if o.name in bpy.context.view_layer.objects else None, o.hide_render, tuple(round(x,3) for x in o.location), tuple(round(x,3) for x in o.scale), o.parent.name if o.parent else None)
ob = bpy.data.objects["bot"]
print(len(ob.data.vertices), len(ob.data.polygons), [m.name for m in ob.data.materials], [g.name for g in ob.vertex_groups], [m.type for m in ob.modifiers])
print(ob.matrix_world)
rig = bpy.data.objects["bot_rig"]
print(rig.matrix_world)
for b in rig.data.bones:
    print(b.name, b.parent.name if b.parent else None, tuple(round(x,4) for x in b.head_local), tuple(round(x,4) for x in b.tail_local), b.use_deform)
print([a.name for a in bpy.data.actions], rig.animation_data.action.name if rig.animation_data and rig.animation_data.action else None)
print([i.name for i in bpy.data.images])
print(bpy.context.scene.render.engine, [o.name for o in bpy.data.objects if o.type in ("LIGHT","CAMERA")])
