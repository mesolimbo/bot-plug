# Checks on the reduced bot_new against bot_new_full: mesh health, glow faces, two-way surface error (all and visible-only).
import bpy, bmesh, math, random, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from collections import Counter
rig = bpy.data.objects["bot_rig"]; pp = rig.data.pose_position; rig.data.pose_position = "REST"; bpy.context.view_layer.update()
OLD, NEW, FLAP = bpy.data.objects["bot_new_full"], bpy.data.objects["bot_new"], bpy.data.objects["bot_flap"]
def health(o):
    me = o.data; bm = bmesh.new(); bm.from_mesh(me)
    r = dict(verts=len(bm.verts), tris=sum(len(f.verts) - 2 for f in bm.faces), boundary=sum(1 for e in bm.edges if len(e.link_faces) == 1),
             nonmanifold=sum(1 for e in bm.edges if len(e.link_faces) > 2), wire=sum(1 for e in bm.edges if not e.link_faces),
             loose_verts=sum(1 for v in bm.verts if not v.link_edges), zero_area=sum(1 for f in bm.faces if f.calc_area() < 1e-12),
             ngons=sum(1 for f in bm.faces if len(f.verts) > 4))
    # loose parts
    seen = set(); n = 0
    for v in bm.verts:
        if v.index in seen: continue
        n += 1; st = [v]; seen.add(v.index)
        while st:
            w = st.pop()
            for e in w.link_edges:
                u = e.other_vert(w)
                if u.index not in seen: seen.add(u.index); st.append(u)
    r["parts"] = n
    bmesh.ops.triangulate(bm, faces=bm.faces)
    ar = []
    for f in bm.faces:
        l = sorted(e.calc_length() for e in f.edges); a = f.calc_area()
        ar.append(l[2] * l[2] / max(4 * a / math.sqrt(3), 1e-18))
    ar = np.array(ar); r["tri_aspect_median"] = round(float(np.median(ar)), 2); r["tris_aspect_over_50"] = int((ar > 50).sum())
    bm.free()
    cp = me.copy(); r["validate_changed"] = cp.validate(); bpy.data.meshes.remove(cp)
    r["bad_weights"] = sum(1 for v in me.vertices if len(v.groups) != 1 or abs(v.groups[0].weight - 1) > 1e-6)
    r["materials"] = dict(Counter((me.materials[p.material_index].name if me.materials[p.material_index] else None) for p in me.polygons))
    return r
for o in (OLD, NEW):
    print(o.name, health(o))
def tri(objs):
    V, P, M = [], [], []
    for o in objs:
        bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.triangulate(bm, faces=bm.faces); mw = o.matrix_world; b = len(V)
        V += [mw @ v.co for v in bm.verts]; names = [m.name if m else "" for m in o.data.materials]
        for f in bm.faces:
            P.append([b + v.index for v in f.verts]); M.append(names[f.material_index])
        bm.free()
    return V, P, M
random.seed(1)
DIRS = []
while len(DIRS) < 40:
    d = Vector((random.gauss(0, 1), random.gauss(0, 1), random.gauss(0, 1)))
    if d.length > 1e-3: DIRS.append(d.normalized())
def analyse(V, P, M, occl):
    """sample points with normals, flag the ones that can be seen from outside"""
    S, N, MM = [], [], []
    for p, m in zip(P, M):
        a, b, c = (V[i] for i in p); n = (b - a).cross(c - a)
        if n.length < 1e-14: continue
        n.normalize()
        for w in ((1/3, 1/3, 1/3), (0.6, 0.2, 0.2), (0.2, 0.6, 0.2), (0.2, 0.2, 0.6), (0.98, 0.01, 0.01), (0.01, 0.98, 0.01), (0.01, 0.01, 0.98), (0.5, 0.5, 0), (0, 0.5, 0.5), (0.5, 0, 0.5)):
            S.append(a * w[0] + b * w[1] + c * w[2]); N.append(n); MM.append(m)
    vis = np.zeros(len(S), bool)
    for i, (s, n) in enumerate(zip(S, N)):
        o = s + n * 2e-4
        for d in DIRS:
            if d.dot(n) > 0.15 and occl.ray_cast(o, d, 3.0)[0] is None:
                vis[i] = True; break
    return S, np.array(MM), vis
Vf, Pf, Mf = tri([FLAP])
Vo, Po, Mo = tri([OLD]); Vn, Pn, Mn = tri([NEW])
bo, bn = BVHTree.FromPolygons(Vo, Po), BVHTree.FromPolygons(Vn, Pn)
oo = BVHTree.FromPolygons(Vo + Vf, Po + [[i + len(Vo) for i in p] for p in Pf]); on = BVHTree.FromPolygons(Vn + Vf, Pn + [[i + len(Vn) for i in p] for p in Pf])
So, Mo2, viso = analyse(Vo, Po, Mo, oo); Sn, Mn2, visn = analyse(Vn, Pn, Mn, on)
d_on = np.array([bn.find_nearest(p)[3] for p in So]) * 1000; d_no = np.array([bo.find_nearest(p)[3] for p in Sn]) * 1000
def line(tag, d):
    return "%s p50 %.3f p95 %.3f p99.5 %.3f max %.3f (n %d, over 1 mm: %d)" % (tag, np.percentile(d, 50), np.percentile(d, 95), np.percentile(d, 99.5), d.max(), len(d), int((d > 1).sum())) if len(d) else tag + " none"
print("visible fraction old %.2f new %.2f" % (viso.mean(), visn.mean()))
print(line("ALL      old->new", d_on)); print(line("ALL      new->old", d_no))
print(line("VISIBLE  old->new", d_on[viso])); print(line("VISIBLE  new->old", d_no[visn]))
for m in sorted(set(Mo) | set(Mn)):
    print("  %-14s" % m, line("vis old->new", d_on[viso & (Mo2 == m)]), "|", line("vis new->old", d_no[visn & (Mn2 == m)]))
def clusters(tag, S, d, mask, mats, thr):
    cl = {}
    for i in np.nonzero(mask & (d > thr))[0]:
        p = S[i]; k = (round(p.x / 0.03), round(p.y / 0.03), round(p.z / 0.03))
        if k not in cl or cl[k][0] < d[i]: cl[k] = [d[i], p, mats[i], cl.get(k, [0, 0, 0, 0])[3]]
        cl[k][3] += 1
    print(tag, "over %.1f mm:" % thr, [("%.2f" % a, tuple(round(c, 3) for c in p), m.replace("botn_", ""), n) for a, p, m, n in sorted(cl.values(), key=lambda x: -x[0])[:25]])
clusters("VISIBLE old->new", So, d_on, viso, Mo2, 1.0); clusters("VISIBLE new->old", Sn, d_no, visn, Mn2, 1.0)
clusters("HIDDEN  old->new", So, d_on, ~viso, Mo2, 3.0); clusters("HIDDEN  new->old", Sn, d_no, ~visn, Mn2, 3.0)
# holes: rays down the socket bore, the three pin holes, and through the middle of each opening must hit what they hit before
names_o = Mo; names_n = Mn
for tag, org, d in [("pin top", (-0.30, 0.0015, 0.043), (1, 0, 0)), ("pin L", (-0.30, -0.0105 + 0.0015, 0.025), (1, 0, 0)), ("pin R", (-0.30, 0.0105 + 0.0015, 0.025), (1, 0, 0)),
                    ("bore", (-0.30, 0.025, 0.030), (1, 0, 0)), ("bore2", (-0.30, -0.02, 0.012), (1, 0, 0)), ("face", (0.40, 0.05, 0.10), (-1, 0, 0)),
                    ("hip well L", (0.02, 0.40, -0.06), (0, -1, 0)), ("hip well R", (0.02, -0.40, -0.06), (0, 1, 0)), ("vent front", (0.14, 0.03, 0.60), (0, 0, -1)), ("vent rear", (-0.15, 0.03, 0.60), (0, 0, -1)),
                    ("slot L", tuple(Vector((0, 0, 0.08)) + Vector((math.cos(math.radians(35)) * math.cos(math.radians(23.5)), math.cos(math.radians(35)) * math.sin(math.radians(23.5)), math.sin(math.radians(35)))) * 0.5), tuple(-Vector((math.cos(math.radians(35)) * math.cos(math.radians(23.5)), math.cos(math.radians(35)) * math.sin(math.radians(23.5)), math.sin(math.radians(35))))))]:
    ho, hn = bo.ray_cast(Vector(org), Vector(d), 1.0), bn.ray_cast(Vector(org), Vector(d), 1.0)
    print("ray %-10s old hit %s %s | new hit %s %s" % (tag, tuple(round(c, 4) for c in ho[0]) if ho[0] else None, Mo[ho[2]] if ho[0] else "", tuple(round(c, 4) for c in hn[0]) if hn[0] else None, Mn[hn[2]] if hn[0] else ""))
rig.data.pose_position = pp
