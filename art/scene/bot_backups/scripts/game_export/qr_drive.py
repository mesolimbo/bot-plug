"""Quad Remesh each large part in turn through the Blender bridge, checking each result against its original."""
import json, socket, sys, time

TOL, MIN_TRIS = 0.0012, 500

def send(code):
    with socket.create_connection(("127.0.0.1", 9876), timeout=900) as s:
        s.sendall(code.encode("utf-8")); s.shutdown(socket.SHUT_WR)
        data = b""
        while chunk := s.recv(65536):
            data += chunk
    r = json.loads(data)
    if not r["ok"]:
        raise RuntimeError(r["error"])
    return r["output"].strip()

PRE = '''
import bpy, bmesh
from mathutils.bvhtree import BVHTree
win = bpy.context.window_manager.windows[0]
area = next(a for a in win.screen.areas if a.type == "VIEW_3D")
region = next(r for r in area.regions if r.type == "WINDOW")
'''
names = json.loads(send(PRE + 'import json\nprint(json.dumps([o.name for o in sorted(bpy.data.collections["bot_qr"].objects, key=lambda o: o.name) if o.name.startswith("qp_") and o["tris"] >= %d]))' % MIN_TRIS))
only = sys.argv[1:]
if only:
    names = [n for n in names if n in only]

LAUNCH = PRE + '''
name, count = %r, %d
old = bpy.data.objects.get("Retopo_" + name)
if old:
    me = old.data; bpy.data.objects.remove(old, do_unlink=True); bpy.data.meshes.remove(me)
src = bpy.data.objects[name]
src.hide_set(False)
qr = bpy.context.scene.qremesher
qr.target_count = count; qr.adaptive_size = 50.0; qr.adapt_quad_count = True
qr.autodetect_hard_edges = True; qr.use_materials = True; qr.use_normals = False
qr.symmetry_x = qr.symmetry_y = qr.symmetry_z = False; qr.hide_input = False
for o in bpy.context.view_layer.objects:
    o.select_set(False)
src.select_set(True); bpy.context.view_layer.objects.active = src
with bpy.context.temp_override(window=win, area=area, region=region, active_object=src, selected_objects=[src]):
    print(bpy.ops.qremesher.remesh())
'''
POLL = PRE + 'print("yes" if bpy.data.objects.get("Retopo_%s") else "no")'
EVAL = PRE + '''
name = %r
src, out = bpy.data.objects[name], bpy.data.objects["Retopo_" + name]
def pts(bm):
    return [v.co.copy() for v in bm.verts] + [f.calc_center_median() for f in bm.faces] + [(e.verts[0].co + e.verts[1].co) / 2 for e in bm.edges]
a = bmesh.new(); a.from_mesh(src.data); a.transform(src.matrix_world); ta = BVHTree.FromBMesh(a)
b = bmesh.new(); b.from_mesh(out.data); b.transform(out.matrix_world); tb = BVHTree.FromBMesh(b)
e1 = sorted((tb.find_nearest(p)[3] or 0) for p in pts(a)); e2 = sorted((ta.find_nearest(p)[3] or 0) for p in pts(b))
tris = sum(len(f.verts) - 2 for f in b.faces)
print("%%.5f %%.5f %%d" %% (max(e1[int(len(e1) * 0.995)], e2[int(len(e2) * 0.995)]), max(e1[-1], e2[-1]), tris))
src.hide_set(True); out.hide_set(True)
'''
results = {}
for name in names:
    tris = int(send(PRE + 'print(bpy.data.objects[%r]["tris"])' % name))
    count = max(120, tris // 10)
    for attempt in range(3):
        send(LAUNCH % (name, count))
        t = time.time()
        while send(POLL % name) != "yes":
            if time.time() - t > 240:
                break
            time.sleep(1.5)
        else:
            e995, emax, rt = send(EVAL % name).split()
            e995, emax, rt = float(e995), float(emax), int(rt)
            ok = e995 <= TOL and emax <= TOL * 3
            print(f"{name}: {tris} -> {rt} tris (quads {count}), err p99.5 {e995*1000:.2f} mm max {emax*1000:.2f} mm {'OK' if ok else 'retry'}", flush=True)
            if ok:
                results[name] = rt; break
            count *= 2
            continue
        print(f"{name}: timed out", flush=True)
        count *= 2
    else:
        results[name] = None
        print(f"{name}: keeping original", flush=True)
print("done", json.dumps(results))
