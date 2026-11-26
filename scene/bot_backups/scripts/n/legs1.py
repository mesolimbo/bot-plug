# temp objects of the old left leg (whole and per bone), then close-up renders
old = bpy.data.objects["bot"]
gi = {g.name: g.index for g in old.vertex_groups}


def sub_obj(name, groups):
    o = bpy.data.objects.get(name)
    if o:
        me = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.meshes.remove(me)
    bm = bmesh.new()
    bm.from_mesh(old.data)
    dl = bm.verts.layers.deform.active
    ids = {gi[g] for g in groups}
    rem = [v for v in bm.verts if not (len(v[dl]) and max(v[dl].items(), key=lambda kv: kv[1])[0] in ids)]
    bmesh.ops.delete(bm, geom=rem, context="VERTS")
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in old.data.materials:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    scene.collection.objects.link(o)
    o.hide_set(True)
    o.hide_render = True
    return o


sub_obj("old_legL", ["thigh.L", "shin.L", "foot.L"])
sub_obj("old_thighL", ["thigh.L"])
sub_obj("old_shinL", ["shin.L"])
sub_obj("old_footL", ["foot.L"])
sub_obj("old_body", ["body"])
Y = 0.1033
S_ = {
    "lg_out": ((0.02, 3, -0.28), (0.02, Y, -0.28), 0.5),
    "lg_in": ((0.02, -3, -0.28), (0.02, Y, -0.28), 0.5),
    "lg_front": ((3, Y, -0.28), (0, Y, -0.28), 0.5),
    "lg_back": ((-3, Y, -0.28), (0, Y, -0.28), 0.5),
    "lg_q1": ((2, 2 + Y, 0.6), (0.02, Y, -0.28), 0.5),
    "lg_q2": ((-2, 2 + Y, 0.6), (0.02, Y, -0.28), 0.5),
    "lg_top": ((0.02, Y, 3), (0.02, Y, -0.28), 0.36),
    "lg_q3": ((2, -2 + Y, 0.3), (0.02, Y, -0.28), 0.5),
}


def shots(obname, shots, prefix, tex=True, res=1000):
    ob = bpy.data.objects[obname]
    hidden = {o.name: o.hide_render for o in bpy.data.objects}
    only_render([obname])
    saved = list(ob.data.materials)
    if tex:
        setup_tex(res)
        ob.data.materials.clear(); ob.data.materials.append(view_mat("bot_baked"))
    else:
        setup_wb(res, False, "SINGLE")
        scene.display.shading.single_color = (0.8, 0.8, 0.8)
    for name, (loc, tgt, ortho) in shots.items():
        shoot(VD + "\\" + prefix + name + ".png", loc, tgt, ortho, "X" if abs(loc[0] - tgt[0]) < 1e-6 and abs(loc[1] - tgt[1]) < 1e-6 else "Y")
    ob.data.materials.clear()
    for m in saved:
        ob.data.materials.append(m)
    for o in bpy.data.objects:
        o.hide_render = hidden.get(o.name, o.hide_render)


shots("old_legL", S_, "t", True)
shots("old_legL", S_, "g", False)
print("legs shot")
