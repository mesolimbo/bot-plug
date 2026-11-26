bm = cube_sphere(64, 1.0)
inner = cube_sphere(32, 0.97)
bmesh.ops.reverse_faces(inner, faces=inner.faces)
me_in = bpy.data.meshes.new("tmp_in"); inner.to_mesh(me_in); inner.free()
bm.from_mesh(me_in); bpy.data.meshes.remove(me_in)
t = tmp_obj("dbg_unit", bm)
def has():
    b = bmesh.new(); b.from_mesh(t.data); bv = BVHTree.FromBMesh(b)
    h = bv.ray_cast(Vector((0,0,0)) + D(0,37)*0.98, D(0, 37)); b.free()
    return h[0] is not None
print("start", has())
for name, loop in OPENINGS:
    boolean(t, cone_cutter(loop, name="cut_" + name)); print(name, has(), len(t.data.vertices))
for name, path in list(SLOTS.items()) + list(SEAMS.items()):
    boolean(t, ribbon_cutter(path, SLOT_HW if "slot" in name else HW, name="cut_" + name)); print(name, has(), len(t.data.vertices))
me = t.data; bpy.data.objects.remove(t, do_unlink=True); bpy.data.meshes.remove(me)
