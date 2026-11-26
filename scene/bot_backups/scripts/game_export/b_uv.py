import bpy, math
win = bpy.context.window_manager.windows[0]
area = next(a for a in win.screen.areas if a.type == "VIEW_3D")
region = next(r for r in area.regions if r.type == "WINDOW")
low = bpy.data.objects["bot_game"]
me = low.data
for p in me.polygons:
    p.use_smooth = True
for nm in ("sharp_edge", "sharp_face"):
    a = me.attributes.get(nm)
    if a:
        me.attributes.remove(a)
if me.has_custom_normals:
    me.normals_split_custom_set([])  # noqa
while me.uv_layers:
    me.uv_layers.remove(me.uv_layers[0])
me.uv_layers.new(name="UVMap")
for o in bpy.context.view_layer.objects:
    o.select_set(False)
low.select_set(True)
bpy.context.view_layer.objects.active = low
with bpy.context.temp_override(window=win, area=area, region=region, object=low, active_object=low, selected_objects=[low], selected_editable_objects=[low]):
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.0, area_weight=0.0, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(rotate=True, margin=0.004)
    bpy.ops.object.mode_set(mode="OBJECT")
S = 4096
def img(name, size, noncolor=False):
    im = bpy.data.images.get(name)
    if im and tuple(im.size) != (size, size):
        bpy.data.images.remove(im); im = None
    im = im or bpy.data.images.new(name, size, size, alpha=False)
    im.colorspace_settings.name = "Non-Color" if noncolor else "sRGB"
    return im
img("bg_col_on", S); img("bg_col_off", S); img("bg_dec_col", S); img("bg_dec_a", S, True)
img("bg_ao", 2048, True); img("bg_lit", 2048, True); img("bg_emit", 2048, True)
m = bpy.data.materials.get("bot_game_mat") or bpy.data.materials.new("bot_game_mat")
m.use_nodes = True
nt = m.node_tree; nt.nodes.clear()
out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled")
t = nt.nodes.new("ShaderNodeTexImage"); t.name = "bake"; t.image = bpy.data.images["bg_col_on"]
nt.links.new(t.outputs["Color"], b.inputs["Base Color"]); nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])
nt.nodes.active = t
names = [x.name if x else "" for x in me.materials]
glow = [names[p.material_index] == "bot_glow" for p in me.polygons]
a = me.attributes.get("glow") or me.attributes.new("glow", "BOOLEAN", "FACE")
a.data.foreach_set("value", glow)
print("glow faces", sum(glow))
me.materials.clear(); me.materials.append(m)
for p in me.polygons:
    p.material_index = 0
print("uv ok; islands packed; verts", len(me.vertices), "devices", bpy.context.preferences.addons["cycles"].preferences.compute_device_type)
