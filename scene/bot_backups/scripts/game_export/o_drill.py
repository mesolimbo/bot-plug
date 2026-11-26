# Drill the three pin holes through the rubber cup floor (the clover's cutters never reached it).
import bpy, bmesh, math
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
win = bpy.context.window_manager.windows[0]
area = next(a for a in win.screen.areas if a.type == "VIEW_3D")
region = next(r for r in area.regions if r.type == "WINDOW")
o = bpy.data.objects["bot_new"]; me = o.data
names = [m.name for m in me.materials]
bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
bvh = BVHTree.FromBMesh(bm)
s = bm.faces[bvh.ray_cast(Vector((-0.30, 0.0015, 0.043)), Vector((1, 0, 0)), 0.2)[2]]
st = [s]; seen = {s.index}; fs = []
while st:
    g = st.pop(); fs.append(g)
    for e in g.edges:
        for k in e.link_faces:
            if k.index not in seen: seen.add(k.index); st.append(k)
assert len(fs) == 144 and all(names[f.material_index] == "botn_rubber" for f in fs), len(fs)
bmesh.ops.delete(bm, geom=fs, context="FACES")
bm.to_mesh(me); bm.free(); me.update()

# rebuild the floor as its own object, drilled
FLOOR, BORE, Z = -0.2385, 0.0328, 0.030
disc = bmesh.new()
bmesh.ops.create_cone(disc, cap_ends=True, segments=48, radius1=BORE + 0.0006, radius2=BORE + 0.0006, depth=0.004,
                      matrix=Matrix.Translation((FLOOR + 0.002, 0, Z)) @ Matrix.Rotation(math.pi / 2, 4, "Y"))
dme = bpy.data.meshes.new("tmp_disc"); disc.to_mesh(dme); disc.free()
dob = bpy.data.objects.new("tmp_disc", dme); bpy.context.scene.collection.objects.link(dob)
cut = bmesh.new()
for y, z in [(0.0, 0.042), (-0.0105, 0.024), (0.0105, 0.024)]:
    bmesh.ops.create_cone(cut, cap_ends=True, segments=24, radius1=0.004, radius2=0.004, depth=0.01,
                          matrix=Matrix.Translation((FLOOR + 0.002, y, z)) @ Matrix.Rotation(math.pi / 2, 4, "Y"))
cme = bpy.data.meshes.new("tmp_cut"); cut.to_mesh(cme); cut.free()
cob = bpy.data.objects.new("tmp_cut", cme); bpy.context.scene.collection.objects.link(cob)
mod = dob.modifiers.new("drill", "BOOLEAN"); mod.operation = "DIFFERENCE"; mod.solver = "EXACT"; mod.object = cob
for x in bpy.context.view_layer.objects: x.select_set(False)
dob.select_set(True); bpy.context.view_layer.objects.active = dob
with bpy.context.temp_override(window=win, area=area, region=region, object=dob, active_object=dob, selected_objects=[dob], selected_editable_objects=[dob]):
    bpy.ops.object.modifier_apply(modifier="drill")
bpy.data.objects.remove(cob, do_unlink=True); bpy.data.meshes.remove(cme)
for m in me.materials:
    dme.materials.append(m)
ri, gi = names.index("botn_rubber"), names.index("bot_glow")
ng = 0
for p in dme.polygons:
    c = p.center
    inner = min(math.hypot(c.y - y, c.z - z) for y, z in [(0.0, 0.042), (-0.0105, 0.024), (0.0105, 0.024)]) < 0.0041
    p.material_index = gi if inner else ri
    p.use_smooth = False
    ng += inner
vg = dob.vertex_groups.new(name="body"); vg.add(range(len(dme.vertices)), 1.0, "REPLACE")
# join into bot_new (bot_new is bone-parented to the rig at identity, so world space matches)
for x in bpy.context.view_layer.objects: x.select_set(False)
o.hide_set(False); o.select_set(True); dob.select_set(True); bpy.context.view_layer.objects.active = o
with bpy.context.temp_override(window=win, area=area, region=region, object=o, active_object=o, selected_objects=[o, dob], selected_editable_objects=[o, dob]):
    bpy.ops.object.join()
print("drilled floor: faces", len(dme.polygons) if dme.name in bpy.data.meshes else "joined", "glow walls", ng)
bvh2 = bmesh.new(); bvh2.from_mesh(me); t = BVHTree.FromBMesh(bvh2)
for y, z in [(0.0, 0.042), (-0.0105, 0.024), (0.0105, 0.024)]:
    h = t.ray_cast(Vector((-0.30, y + 0.0015, z + 0.001)), Vector((1, 0, 0)), 0.2)
    print("first hit down hole at x %.4f" % h[0].x)
bvh2.free()
