# ---- fidelity numbers: distance between the new parts and the old mesh (rest pose), both directions ---------
import json
old = bpy.data.objects["bot"]
bmo = bmesh.new(); bmo.from_mesh(old.data)
bvo = BVHTree.FromBMesh(bmo)
INTERNAL = ("core", "liner", "seam_floors", "socket_cup", "socket_frame", "top_ring")


def pct(ds):
    ds = sorted(ds)
    n = len(ds)
    return {"n": n, "median_mm": round(ds[n // 2] * 1000, 2), "p90_mm": round(ds[int(n * 0.9)] * 1000, 2), "p99_mm": round(ds[int(n * 0.99)] * 1000, 2), "max_mm": round(ds[-1] * 1000, 2)}


stats = {}
groups = {"shell panel tops": [], "top (dome, ring, collar, lugs, antenna)": [], "vents (ribs, louvres)": [], "face (bezel, screen, lights)": [],
          "rear socket and dust cover": [], "legs": [], "ALL EXTERNAL": []}
tv, tf = [], []
for ob in coll().objects:
    if ob.type != "MESH" or ob.name.startswith(("tmp", "cut_", "cc_")):
        continue
    n = ob.name.split(".")[0]
    mw = ob.matrix_world
    me = ob.data
    if n == "shell":
        wall = ORDER.index("dark")
        keep = set()
        for p in me.polygons:
            if p.material_index != wall:
                keep.update(p.vertices)
        vs = [mw @ me.vertices[i].co for i in keep]
    else:
        vs = [mw @ v.co for v in me.vertices]
    ds = [bvo.find_nearest(v)[3] for v in vs]
    if n in INTERNAL:
        continue
    key = ("shell panel tops" if n == "shell" else "top (dome, ring, collar, lugs, antenna)" if n in ("dome", "ring_teeth", "collar", "lug0", "lug1") or n.startswith("antenna")
           else "vents (ribs, louvres)" if n in ("louvres", "vent_ribs") else "face (bezel, screen, lights)" if n in ("bezel", "screen") or n.startswith(("pill", "face_bar", "corner_light"))
           else "rear socket and dust cover" if n.startswith(("socket", "flap", "hinge")) else "legs")
    groups[key] += ds
    groups["ALL EXTERNAL"] += ds
    base = len(tv)
    tv.extend(mw @ v.co for v in me.vertices)
    tf.extend([base + i for i in p.vertices] for p in me.polygons)
for k, ds in groups.items():
    if ds:
        stats["new->old " + k] = pct(ds)
bvn = BVHTree.FromPolygons(tv, tf)
gi = {g.index: g.name for g in old.vertex_groups}
rev = {"body": [], "legs": []}
for v in old.data.vertices:
    g = max(v.groups, key=lambda x: x.weight).group if v.groups else -1
    d = bvn.find_nearest(v.co)[3]
    rev["body" if gi.get(g) == "body" else "legs"].append(d)
for k, ds in rev.items():
    stats["old->new " + k] = pct(ds)
stats["old->new ALL"] = pct(rev["body"] + rev["legs"])
bmo.free()
json.dump(stats, open(SP + r"\n\stats.json", "w"), indent=1)
for k, v in stats.items():
    print(k, v)
