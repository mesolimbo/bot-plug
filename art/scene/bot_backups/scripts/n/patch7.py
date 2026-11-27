p = "n/b9_final.py"
s = open(p, encoding="utf-8").read()
a = s.index("    mw = flap_src.matrix_world.copy()")
b = s.index("    edit_op(flap_src, lambda: bpy.ops.uv.pack_islands(margin=0.01))")
s = s[:a] + '''    pb = rig.pose.bones["body"]
    parent_world = rig.matrix_world @ pb.matrix @ Matrix.Translation((0, pb.bone.length, 0))
    flap_src.parent = rig
    flap_src.parent_type = "BONE"
    flap_src.parent_bone = "body"
    flap_src.matrix_parent_inverse = parent_world.inverted()      # keeps location = hinge axis, rotation Y = lid angle
''' + s[b:]
open(p, "w", encoding="utf-8").write(s)
print("ok")
