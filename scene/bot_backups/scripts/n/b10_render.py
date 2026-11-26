# ---- lit renders of the new bot (and unlit textured renders of the old one at the same framing) -------------
import os
RD = SP + r"\renders"
os.makedirs(RD, exist_ok=True)
new_names = [o.name for o in bpy.data.collections["botn"].all_objects if o.type == "MESH"]
rig = bpy.data.objects["bot_rig"]

# lights
lc = bpy.data.collections.get("botn_lights")
if lc:
    for o in list(lc.objects):
        d = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.lights.remove(d)
    bpy.data.collections.remove(lc)
    lc = None
if not lc:
    lc = bpy.data.collections.new("botn_lights")
    scene.collection.children.link(lc)
    def light(name, kind, energy, loc, size=1.0, color=(1, 1, 1)):
        d = bpy.data.lights.new(name, kind)
        d.energy = energy
        d.color = color
        if kind == "AREA":
            d.size = size
        if kind == "SUN":
            d.angle = math.radians(8)
        o = bpy.data.objects.new(name, d)
        lc.objects.link(o)
        o.location = loc
        o.rotation_euler = (Vector((0, 0, 0.05)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        return o
    light("key", "SUN", 1.45, (2.0, 1.6, 3.0))
    light("fill", "AREA", 45, (1.5, -2.2, 0.8), 2.5, (0.9, 0.95, 1.0))
    light("rim", "AREA", 70, (-2.2, 0.6, 1.6), 2.0)
    light("under", "AREA", 22, (0.3, 0.0, -1.8), 3.0)
world = bpy.data.worlds.get("botn_world") or bpy.data.worlds.new("botn_world")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.30, 0.32, 0.36, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.45


def setup_lit(res=1200):
    scene.world = world
    try:
        scene.render.engine = "BLENDER_EEVEE"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    for o in lc.objects:
        o.hide_render = False


def lit(shots, res=1200, prefix="new_", extra=()):
    hidden = {o.name: o.hide_render for o in bpy.data.objects}
    only_render(list(new_names) + list(extra))
    setup_lit(res)
    for name, (loc, tgt, ortho) in shots.items():
        shoot(RD + "\\" + prefix + name + ".png", loc, tgt, ortho, "X" if abs(loc[0] - tgt[0]) < 1e-6 and abs(loc[1] - tgt[1]) < 1e-6 else "Y")
    for o in bpy.data.objects:
        o.hide_render = hidden.get(o.name, o.hide_render)


def old_unlit(shots, res=1200, prefix="old_"):
    ob = bpy.data.objects["bot"]
    hidden = {o.name: o.hide_render for o in bpy.data.objects}
    only_render(["bot"])
    setup_tex(res)
    scene.world = bpy.data.worlds.get("proj_world") or world
    for o in lc.objects:
        o.hide_render = True
    saved = list(ob.data.materials)
    ob.data.materials.clear(); ob.data.materials.append(view_mat("bot_baked"))
    for name, (loc, tgt, ortho) in shots.items():
        shoot(RD + "\\" + prefix + name + ".png", loc, tgt, ortho, "X" if abs(loc[0] - tgt[0]) < 1e-6 and abs(loc[1] - tgt[1]) < 1e-6 else "Y")
    ob.data.materials.clear()
    for m in saved:
        ob.data.materials.append(m)
    for o in bpy.data.objects:
        o.hide_render = hidden.get(o.name, o.hide_render)


WHOLE = {"front": ((3, 0, 0.0), (0, 0, 0.0), 1.08), "back": ((-3, 0, 0.0), (0, 0, 0.0), 1.08), "side": ((0, 3, 0.0), (0, 0, 0.0), 1.08),
         "q34": ((2.2, 1.9, 1.3), (0, 0, -0.01), 1.08), "q34_back": ((-2.2, 1.9, 1.3), (0, 0, -0.01), 1.08), "top": ((0, 0, 3), (0, 0, 0.1), 0.62)}
CLOSE = {"face": ((3, 0, 0.073), (0, 0, 0.073), 0.40), "face_q": ((2.4, 1.3, 0.5), (0.2, 0.02, 0.073), 0.40), "pill": ((2, 0.5, 0.05), (0.24, 0.147, 0.05), 0.11),
         "socket": ((-3, 0, 0.03), (0, 0, 0.03), 0.30), "socket_close": ((-3, 0, 0.03), (0, 0, 0.03), 0.12), "socket_q": ((-2, 0.9, 0.9), (-0.25, 0, 0.03), 0.16),
         "chevron": ((-3, 0, 0.6), (-0.2, 0, 0.15), 0.46), "vent_front": ((0.9, 0, 1.2), (0.165, 0, 0.275), 0.26), "vent_rear": ((-0.9, 0, 1.2), (-0.165, 0, 0.27), 0.26),
         "vent_top": ((0, 0, 2), (-0.02, 0, 0.3), 0.32), "vent_side": ((0.3, 1.2, 1.4), (-0.03, 0.16, 0.29), 0.26),
         "seams_left": ((0.4, 2, 0.9), (-0.02, 0.2, 0.15), 0.36), "seams_rear": ((-1.6, 1.6, 0.3), (-0.17, 0.17, 0.05), 0.36), "under": ((0.4, 0, -3), (0, 0, -0.05), 0.60),
         "leg": ((0.5, 3, -0.27), (0.02, 0.1, -0.27), 0.52), "top_rear_quarter": ((-1.6, -1.0, 1.9), (-0.06, -0.04, 0.3), 0.34),
         "rear_above_vents": ((-1.8, 0.6, 1.5), (-0.1, 0.03, 0.28), 0.30), "top_front_quarter": ((1.6, 0.8, 1.7), (0.08, 0.04, 0.29), 0.34),
         "receptacle": ((-2, 0.5, 0.5), (-0.25, 0, 0.03), 0.09), "ring_straight": ((-2.26, 0, 0.03), (-0.26, 0, 0.03), 0.11),
         "ring_oblique_side": ((-1.79, 1.286, 0.03), (-0.26, 0, 0.03), 0.11), "ring_oblique_above": ((-1.79, 0, 1.316), (-0.26, 0, 0.03), 0.11), "leg_q": ((2.2, 2.2, 0.3), (0.02, 0.1, -0.27), 0.52)}
rig.data.pose_position = "REST"
bpy.context.view_layer.update()
lit(WHOLE)
lit(CLOSE)
old_unlit(WHOLE)
old_unlit(CLOSE)

# dust cover closed (temporary), then back to open
fl = bpy.data.objects["bot_flap"]
rot = fl.rotation_euler.y
fl.rotation_euler.y = 0.0
bpy.context.view_layer.update()
lit({"cover_closed": CLOSE["socket"], "cover_closed_q": CLOSE["socket_q"], "cover_closed_side": ((-0.25, 3, 0.02), (-0.25, 0, 0.02), 0.30)})
fl.rotation_euler.y = rot
bpy.context.view_layer.update()
lit({"cover_open_side": ((-0.25, 3, 0.02), (-0.25, 0, 0.02), 0.30)})

# plug seated (temporary copy of the game plug, removed afterwards)
PLUG_BLEND = r"C:\Users\mesol\OneDrive\Documents\Art\2026\Alan's Bot Plugs\scene\plug.blend"
with bpy.data.libraries.load(PLUG_BLEND, link=False) as (src, dst):
    dst.objects = [n for n in src.objects]
tc = bpy.data.collections.new("tmp_plug")
scene.collection.children.link(tc)
for o in dst.objects:
    if o is not None:
        tc.objects.link(o)
plug = next(o for o in tc.objects if o.name.startswith("plug") and o.type == "EMPTY")
plug.location = (-0.245, 0.0, 0.030)
plug.rotation_euler = (0, 0, math.pi)
bpy.context.view_layer.update()
pn = [o.name for o in tc.objects if o.parent is plug and o.type == "MESH"]
lit({"plug_seated": ((-2, 0.9, 0.9), (-0.29, 0, 0.03), 0.26), "plug_seated_side": ((-0.27, 3, 0.03), (-0.27, 0, 0.03), 0.26)}, extra=pn)
# cutaway check: only the receptacle and the plug pins, from the side
hidden = {o.name: o.hide_render for o in bpy.data.objects}
only_render(pn)
for o in bpy.data.objects:
    if o.name in new_names:
        o.hide_render = True
for o in list(tc.objects):
    me = o.data
    bpy.data.objects.remove(o, do_unlink=True)
    if me and getattr(me, "users", 1) == 0 and isinstance(me, bpy.types.Mesh):
        bpy.data.meshes.remove(me)
bpy.data.collections.remove(tc)
for o in bpy.data.objects:
    o.hide_render = hidden.get(o.name, o.hide_render)
for m in list(bpy.data.materials):
    if m.users == 0 and not m.name.startswith(("botn_", "bot_", "view_")):
        bpy.data.materials.remove(m)

# walk cycle frames
rig.data.pose_position = "POSE"
for fr in (1, 7, 13, 19):
    scene.frame_set(fr)
    bpy.context.view_layer.update()
    lit({"walk_f%02d" % fr: WHOLE["q34"], "walk_side_f%02d" % fr: WHOLE["side"]}, res=900)
scene.frame_set(1)
rig.data.pose_position = "REST"
bpy.context.view_layer.update()
for o in lc.objects:
    o.hide_render = False
print("renders done")
