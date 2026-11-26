import bpy, bmesh, math
from mathutils import Vector
o = bpy.data.objects["bot_new"]; me = o.data
bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
# faces of the drilled floor: x between -0.2386 and -0.2344, r < 0.0335
sel = [f for f in bm.faces if -0.2386 <= f.calc_center_median().x <= -0.2344 and math.hypot(f.calc_center_median().y, f.calc_center_median().z - 0.03) < 0.0336
       and all(-0.2386 <= v.co.x <= -0.2344 for v in f.verts)]
front = [f for f in sel if abs(f.calc_center_median().x + 0.2385) < 1e-4]
print("floor faces", len(sel), "front faces", len(front), "front normal x", [round(f.normal.x, 2) for f in front[:4]])
bmesh.ops.recalc_face_normals(bm, faces=sel)
print("after", [round(f.normal.x, 2) for f in front[:4]])
bm.to_mesh(me); bm.free(); me.update()
