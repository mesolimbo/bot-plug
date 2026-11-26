# Blueprint data v2: hidden-line projection of the planned parts (collection botn) in four ortho views,
# old-model textured ortho renders for the underlay, silhouette masks old/new, and a seam-position score.
import json, os
import numpy as np
BP = SP + r"\blueprints"
os.makedirs(BP, exist_ok=True)
VIEWS = {"front": ((0, 1, 0), (0, 0, 1), (1, 0, 0)), "back": ((0, -1, 0), (0, 0, 1), (-1, 0, 0)),
         "side": ((-1, 0, 0), (0, 0, 1), (0, 1, 0)), "top": ((0, -1, 0), (1, 0, 0), (0, 0, 1))}
bpy.data.objects["bot_rig"].data.pose_position = "REST"
bpy.context.view_layer.update()


def cls_of(name, mat_a, mat_b):
    n = name.split(".")[0]
    if n in ("louvres", "vent_ribs", "ring_teeth", "top_ring"):
        return "vent"
    if n.startswith(("pill", "face_bar", "corner_light", "socket_ring", "socket_pins", "socket_leds")):
        return "light"
    if n.startswith(("hip", "thigh", "knee", "shin", "ankle", "toe", "heel", "sole")):
        return "leg"
    if n == "shell":
        return "seam"
    if n in ("core", "liner"):
        return "core"
    return "part"


# gather geometry
tris_v, tris = [], []
edges = []          # (p0, p1, n1, n2 or None, cls, crease, matdiff)
SKIP_EDGES = ("liner",)
for ob in bpy.data.collections["botn"].all_objects:
    if ob.type != "MESH" or ob.name.startswith(("cut_", "cc_", "tmp")):
        continue
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.transform(bm, matrix=ob.matrix_world, verts=bm.verts)
    bm.normal_update()
    base = len(tris_v)
    tris_v.extend(v.co.copy() for v in bm.verts)
    for f in bm.faces:
        vs = [v.index + base for v in f.verts]
        for k in range(1, len(vs) - 1):
            tris.append((vs[0], vs[k], vs[k + 1]))
    if ob.name not in SKIP_EDGES:
        for e in bm.edges:
            lf = e.link_faces
            if len(lf) == 2:
                ang = e.calc_face_angle(0)
                md = lf[0].material_index != lf[1].material_index
                edges.append((e.verts[0].co.copy(), e.verts[1].co.copy(), lf[0].normal.copy(), lf[1].normal.copy(), cls_of(ob.name, 0, 0), ang, md))
            elif len(lf) == 1:
                edges.append((e.verts[0].co.copy(), e.verts[1].co.copy(), lf[0].normal.copy(), None, cls_of(ob.name, 0, 0), 3.14, False))
    bm.free()
bvh = BVHTree.FromPolygons(tris_v, tris)
print("edges", len(edges), "tris", len(tris))

out = {}
CREASE = math.radians(33)
for vname, (r, u, b) in VIEWS.items():
    r, u, b = Vector(r), Vector(u), Vector(b)
    segs = []
    for p0, p1, n1, n2, cls, ang, md in edges:
        d1 = n1.dot(b)
        if n2 is None:
            if d1 <= 0:
                continue
        else:
            d2 = n2.dot(b)
            sil = d1 * d2 < 0
            front = d1 > 0.02 or d2 > 0.02
            if not (sil or (front and (ang > CREASE or md))):
                continue
        L = (p1 - p0).length
        if L < 1e-6:
            continue
        k = max(1, int(L / 0.004))
        vis = []
        for i in range(k + 1):
            p = p0.lerp(p1, i / k)
            h = bvh.ray_cast(p + b * 0.0012, b)
            vis.append(h[0] is None)
        run = None
        for i in range(k + 1):
            if vis[i]:
                if run is None:
                    run = i
            if (not vis[i] or i == k) and run is not None:
                j = i if vis[i] else i - 1
                if j > run or k == 1:
                    a, c = p0.lerp(p1, run / k), p0.lerp(p1, j / k)
                    segs.append([cls, round(a.dot(r), 5), round(a.dot(u), 5), round(c.dot(r), 5), round(c.dot(u), 5)])
                run = None
    out[vname] = segs
    print(vname, len(segs))
json.dump(out, open(BP + r"\bp_lines.json", "w"))

# renders: old textured, old mask, new mask (2 px = 1 mm)
cam = get_cam(); cam.data.ortho_scale = 1.1
old = bpy.data.objects["bot"]
new_names = [o.name for o in bpy.data.collections["botn"].all_objects]
hidden = {o.name: o.hide_render for o in bpy.data.objects}


def setcam(v):
    r, u, b = VIEWS[v]
    cam.matrix_world = Matrix.Translation(Vector(b) * 3) @ Matrix((r, u, b)).transposed().to_4x4()


only_render(["bot"])
setup_tex(2200)
scene.cycles.samples = 8
saved = list(old.data.materials); old.data.materials.clear(); old.data.materials.append(view_mat("bot_baked"))
scene.render.film_transparent = True
scene.render.image_settings.color_mode = "RGBA"
for v in VIEWS:
    setcam(v); scene.render.filepath = BP + "\\oldtex_" + v + ".png"; bpy.ops.render.render(write_still=True)
old.data.materials.clear()
for m in saved:
    old.data.materials.append(m)
setup_wb(1100, True, "SINGLE")
for which, names in (("old", ["bot"]), ("new", new_names)):
    only_render(names)
    for v in VIEWS:
        setcam(v); scene.render.filepath = BP + "\\mask_" + which + "_" + v + ".png"; bpy.ops.render.render(write_still=True)
for o in bpy.data.objects:
    o.hide_render = hidden.get(o.name, o.hide_render)

# seam score: distance from each planned seam centre line to the nearest painted dark line on the old model
col = np.load(SP + r"\n\sph_col.npy")
lum = col.mean(axis=2)
dark = lum < 0.33
H2, W2 = dark.shape
res = {}
alld = []
for name, path in SEAMS.items():
    ds = []
    for d in path[::2]:
        lo, la = lonlat(d)
        j0 = (90 - la) / 180 * H2; i0 = (lo + 180) / 360 * W2
        best = None
        R_ = 16
        cl = max(math.cos(math.radians(la)), 0.2)
        for dj in range(-R_, R_ + 1):
            j = int(j0 + dj)
            if j < 0 or j >= H2:
                continue
            for di in range(-int(R_ / cl), int(R_ / cl) + 1):
                if dark[j, int(i0 + di) % W2]:
                    dist = math.hypot(dj, di * cl) * (180 / H2)
                    if best is None or dist < best:
                        best = dist
        ds.append((best if best is not None else R_ * 180 / H2) * math.pi / 180 * RN * 1000)
    ds.sort(); alld += ds
    res[name] = {"n": len(ds), "median_mm": round(ds[len(ds) // 2], 1), "p90_mm": round(ds[int(len(ds) * 0.9)], 1)}
alld.sort()
res["ALL"] = {"n": len(alld), "median_mm": round(alld[len(alld) // 2], 1), "p90_mm": round(alld[int(len(alld) * 0.9)], 1),
              "within_3mm_pct": round(100 * sum(1 for x in alld if x <= 3) / len(alld), 1), "within_6mm_pct": round(100 * sum(1 for x in alld if x <= 6) / len(alld), 1)}
json.dump(res, open(BP + r"\seam_score.json", "w"), indent=1)
for k, v in res.items():
    print(k, v)
