Y = 0.1033
def cam_shot(path, r, u, b, centre, ortho, res):
    cam = get_cam(); cam.data.ortho_scale = ortho
    R = Matrix((r, u, b)).transposed()
    cam.matrix_world = Matrix.Translation(Vector(centre) + Vector(b) * 3) @ R.to_4x4()
    scene.render.resolution_x = scene.render.resolution_y = res
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
ob = bpy.data.objects["old_legL"]
hidden = {o.name: o.hide_render for o in bpy.data.objects}
only_render(["old_legL"])
setup_tex(1500)
saved = list(ob.data.materials); ob.data.materials.clear(); ob.data.materials.append(view_mat("bot_baked"))
cam_shot(VD + r"\L_side.png", (-1,0,0), (0,0,1), (0,1,0), (0.02, Y, -0.25), 0.56, 1680)
cam_shot(VD + r"\L_inner.png", (1,0,0), (0,0,1), (0,-1,0), (0.02, Y, -0.25), 0.56, 1680)
cam_shot(VD + r"\L_front.png", (0,1,0), (0,0,1), (1,0,0), (0.0, Y, -0.25), 0.56, 1680)
cam_shot(VD + r"\L_back.png", (0,-1,0), (0,0,1), (-1,0,0), (0.0, Y, -0.25), 0.56, 1680)
cam_shot(VD + r"\L_top.png", (0,-1,0), (1,0,0), (0,0,1), (0.02, Y, -0.25), 0.36, 1440)
ob.data.materials.clear()
for m in saved: ob.data.materials.append(m)
for o in bpy.data.objects: o.hide_render = hidden.get(o.name, o.hide_render)
print("ok")
