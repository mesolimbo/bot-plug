PASSES = ["emit"]
import bpy, time
PASSES = globals().get("PASSES", ["col_on"])
G = r"C:\Users\mesol\AppData\Local\Temp\claude\3fec41d04d410712\f1237eee-dce1-4b40-88e6-7a7228eb5a6b\scratchpad\g"
win = bpy.context.window_manager.windows[0]
area = next(a for a in win.screen.areas if a.type == "VIEW_3D")
region = next(r for r in area.regions if r.type == "WINDOW")
sc = bpy.context.scene
rig = bpy.data.objects["bot_rig"]; rig.data.pose_position = "REST"
sc.render.engine = "CYCLES"; sc.cycles.device = "GPU"
low = bpy.data.objects["bot_game"]
hi = [bpy.data.objects["bot_new"], bpy.data.objects["bot_flap"]]
decals = [o for o in bpy.data.objects if o.name.startswith("decal_")]
node = low.data.materials[0].node_tree.nodes["bake"]
for o in hi + decals + [low]:
    o.hide_set(False); o.hide_render = False
bk = sc.render.bake
bk.use_selected_to_active = True; bk.cage_extrusion = 0.0025; bk.max_ray_distance = 0.006
bk.margin = 16; bk.margin_type = "EXTEND"; bk.use_clear = True; bk.target = "IMAGE_TEXTURES"

def screen_image(name):
    for n in bpy.data.materials["botn_screen"].node_tree.nodes:
        if n.type == "TEX_IMAGE":
            n.image = bpy.data.images[name]

def decal_alpha(on):
    for o in decals:
        nt = o.data.materials[0].node_tree
        tex = next(n for n in nt.nodes if n.type == "TEX_IMAGE"); b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        for l in list(b.inputs["Base Color"].links) + list(b.inputs["Alpha"].links):
            nt.links.remove(l)
        if on is None:  # restore
            nt.links.new(tex.outputs["Color"], b.inputs["Base Color"]); nt.links.new(tex.outputs["Alpha"], b.inputs["Alpha"])
        elif on:
            nt.links.new(tex.outputs["Alpha"], b.inputs["Base Color"])
        else:
            nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])

def bake(image, kind, sel, samples, filt=None):
    node.image = bpy.data.images[image]
    sc.cycles.samples = samples
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in sel + [low]:
        o.select_set(True)
    bpy.context.view_layer.objects.active = low
    kw = {"type": kind}
    if filt is not None:
        kw["pass_filter"] = filt
    t = time.time()
    with bpy.context.temp_override(window=win, area=area, region=region, object=low, active_object=low, selected_objects=sel + [low]):
        bpy.ops.object.bake(**kw)
    im = bpy.data.images[image]
    im.filepath_raw = G + "\\" + image + ".png"; im.file_format = "PNG"; im.save()
    print(image, "%.1fs" % (time.time() - t))

for p in PASSES:
    for o in decals:
        o.hide_render = not p.startswith("dec")  # decals must not shade the paint passes
    if p == "col_on":
        screen_image("bot_face_on.png"); bake("bg_col_on", "DIFFUSE", hi, 4, {"COLOR"})
    elif p == "col_off":
        screen_image("bot_face_off.png"); bake("bg_col_off", "DIFFUSE", hi, 4, {"COLOR"}); screen_image("bot_face_on.png")
    elif p == "ao":
        w = sc.world.light_settings; w.distance = 0.06
        bake("bg_ao", "AO", hi, 128)
    elif p == "lit":
        bake("bg_lit", "DIFFUSE", hi, 64, {"DIRECT", "INDIRECT"})
    elif p == "emit":
        bake("bg_emit", "EMIT", hi, 1)
    elif p == "dec_col":
        decal_alpha(False); bake("bg_dec_col", "DIFFUSE", decals, 4, {"COLOR"}); decal_alpha(None)
    elif p == "dec_a":
        decal_alpha(True); bake("bg_dec_a", "DIFFUSE", decals, 4, {"COLOR"}); decal_alpha(None)
node.image = bpy.data.images["bg_col_on"]
for o in decals:
    o.hide_render = False
print("bake done", PASSES)
