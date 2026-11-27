import bpy, os
G = "C:/Users/mesol/AppData/Local/Temp/claude/3fec41d04d410712/f1237eee-dce1-4b40-88e6-7a7228eb5a6b/scratchpad/g"
win = bpy.context.window_manager.windows[0]
area = next(a for a in win.screen.areas if a.type == "VIEW_3D")
region = next(r for r in area.regions if r.type == "WINDOW")
sc = bpy.context.scene
rig = bpy.data.objects["bot_rig"]; low = bpy.data.objects["bot_game"]
rig.data.pose_position = "POSE"
im = bpy.data.images.get("bot_on.jpg")
if im: bpy.data.images.remove(im)
im = bpy.data.images.load(G + "/bot_on.jpg"); im.name = "bot_on.jpg"
nt = bpy.data.materials["bot_game_mat"].node_tree
nt.nodes["bake"].image = im
b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"); b.inputs["Roughness"].default_value = 0.8
me = low.data
if len(me.materials) < 2:
    me.materials.append(bpy.data.materials["bot_glow"])
g = [False] * len(me.polygons); me.attributes["glow"].data.foreach_get("value", g)
for p, v in zip(me.polygons, g):
    p.material_index = 1 if v else 0
import math
ol = me.attributes.get("_outline") or me.attributes.new("_outline", "FLOAT", "POINT")
inside = [0.0 if (-0.2615 < v.co.x < -0.20 and math.hypot(v.co.y, v.co.z - 0.030) < 0.0425) else 1.0 for v in me.vertices]
ol.data.foreach_set("value", inside)
print("no-outline verts", inside.count(0.0))
for m in [m for m in low.modifiers]:
    low.modifiers.remove(m)
low.parent = rig; low.matrix_parent_inverse = rig.matrix_world.inverted()
am = low.modifiers.new("Armature", "ARMATURE"); am.object = rig
hidden = {}
for o in bpy.context.view_layer.objects:
    o.select_set(False)
dec = [o for o in bpy.data.collections["bot_game"].objects if o.name.startswith("bot_decal")]
for o in [low, rig] + dec:
    o.hide_set(False); o.select_set(True)
bpy.context.view_layer.objects.active = rig
sc.frame_set(1)
with bpy.context.temp_override(window=win, area=area, region=region, active_object=rig, selected_objects=[low, rig] + dec):
    bpy.ops.export_scene.gltf(filepath=G + "/bot.glb", export_format="GLB", use_selection=True,
                              export_image_format="AUTO", export_animations=True, export_force_sampling=True,
                              export_frame_range=True, export_anim_single_armature=True, export_attributes=True)
low.hide_set(True)
for o in dec:
    o.hide_set(True)
print("glb", os.path.getsize(G + "/bot.glb"))
