import math, bpy, bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
SP = r"C:\Users\mesol\AppData\Local\Temp\claude\3fec41d04d410712\f1237eee-dce1-4b40-88e6-7a7228eb5a6b\scratchpad"
VD = SP + r"\n\v"
win = bpy.context.window_manager.windows[0]
area = next(a for a in win.screen.areas if a.type == "VIEW_3D")
region = next(r for r in area.regions if r.type == "WINDOW")
scene = bpy.context.scene

def get_cam():
    cam = bpy.data.objects.get("n_cam") or bpy.data.objects.new("n_cam", bpy.data.cameras.new("n_cam"))
    if cam.name not in scene.collection.objects:
        scene.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.clip_start = 0.01
    scene.camera = cam
    return cam

def aim(cam, loc, target, ortho, up="Y"):
    cam.location = Vector(loc)
    cam.data.ortho_scale = ortho
    d = Vector(target) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", up).to_euler()

def only_render(names):
    names = set(names)
    for o in bpy.data.objects:
        if o.type == "MESH":
            o.hide_render = o.name not in names

def view_mat(image):
    mat = bpy.data.materials.get("view_mat") or bpy.data.materials.new("view_mat")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images[image]
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return mat

def setup_tex(res=900):
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 4
    scene.cycles.use_denoising = False
    scene.render.resolution_x = scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    scene.render.image_settings.file_format = "PNG"

def setup_wb(res=900, alpha=False, color="MATERIAL", light="MATCAP"):
    scene.render.engine = "BLENDER_WORKBENCH"
    sh = scene.display.shading
    sh.light = light
    sh.color_type = color
    sh.show_cavity = True
    sh.cavity_type = "BOTH"
    sh.show_object_outline = False
    scene.render.resolution_x = scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = alpha
    scene.view_settings.view_transform = "Standard"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"

def shoot(path, loc, target, ortho, up="Y"):
    cam = get_cam()
    aim(cam, loc, target, ortho, up)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

def old_tex_shots(shots, image="bot_baked", res=900):
    """shots: {name: (loc, target, ortho)} unlit textured renders of old bot."""
    ob = bpy.data.objects["bot"]
    bpy.data.objects["bot_rig"].data.pose_position = "REST"
    hidden = {o.name: o.hide_render for o in bpy.data.objects}
    only_render(["bot"])
    setup_tex(res)
    saved = list(ob.data.materials)
    ob.data.materials.clear(); ob.data.materials.append(view_mat(image))
    try:
        for name, (loc, tgt, ortho) in shots.items():
            shoot(VD + "\\" + name + ".png", loc, tgt, ortho, "X" if abs(loc[0]-tgt[0]) < 1e-6 and abs(loc[1]-tgt[1]) < 1e-6 else "Y")
    finally:
        ob.data.materials.clear()
        for m in saved: ob.data.materials.append(m)
        for o in bpy.data.objects: o.hide_render = hidden.get(o.name, o.hide_render)

def wb_shots(names, shots, res=900, color="SINGLE", alpha=False):
    bpy.data.objects["bot_rig"].data.pose_position = "REST"
    hidden = {o.name: o.hide_render for o in bpy.data.objects}
    only_render(names)
    setup_wb(res, alpha, color)
    scene.display.shading.single_color = (0.8, 0.8, 0.8)
    try:
        for name, (loc, tgt, ortho) in shots.items():
            shoot(VD + "\\" + name + ".png", loc, tgt, ortho, "X" if abs(loc[0]-tgt[0]) < 1e-6 and abs(loc[1]-tgt[1]) < 1e-6 else "Y")
    finally:
        for o in bpy.data.objects: o.hide_render = hidden.get(o.name, o.hide_render)

def new_shots(shots, res=900, light="STUDIO", prefix=""):
    names = [o.name for o in bpy.data.collections["botn"].all_objects]
    hidden = {o.name: o.hide_render for o in bpy.data.objects}
    only_render(names)
    setup_wb(res, False, "MATERIAL", light)
    try:
        for name, (loc, tgt, ortho) in shots.items():
            shoot(VD + "\\" + prefix + name + ".png", loc, tgt, ortho, "X" if abs(loc[0]-tgt[0]) < 1e-6 and abs(loc[1]-tgt[1]) < 1e-6 else "Y")
    finally:
        for o in bpy.data.objects: o.hide_render = hidden.get(o.name, o.hide_render)

STD = {
 "front": ((2,0,0.09),(0,0,0.09),0.62), "back": ((-2,0,0.09),(0,0,0.09),0.62),
 "left": ((0,2,0.09),(0,0,0.09),0.62), "right": ((0,-2,0.09),(0,0,0.09),0.62),
 "top": ((0,0,2),(0,0,0.09),0.62), "under": ((0,0,-2),(0,0,0.09),0.62),
 "q1": ((1.5,1.2,1.2),(0,0,0.12),0.62), "q2": ((-1.5,1.2,1.2),(0,0,0.12),0.62),
 "q3": ((-1.5,-1.2,-0.8),(0,0,0.0),0.62), "q4": ((1.5,-1.2,-0.8),(0,0,0.0),0.62),
}
