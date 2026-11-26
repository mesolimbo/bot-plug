import bpy
for o in list(bpy.data.objects):
    if o.name.startswith(("Retopo_qp_", "qp_")):
        me = o.data; bpy.data.objects.remove(o, do_unlink=True); bpy.data.meshes.remove(me)
qc = bpy.data.collections.get("bot_qr")
if qc: bpy.data.collections.remove(qc)
print("cleaned")
