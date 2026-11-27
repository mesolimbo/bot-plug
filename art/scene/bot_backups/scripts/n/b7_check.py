# ---- watertightness check per object: boundary / non-manifold / loose, normals, signed volume -----------------
import json


def check_mesh(me, mw=None):
    bm = bmesh.new()
    bm.from_mesh(me)
    boundary = sum(1 for e in bm.edges if len(e.link_faces) == 1)
    nonman = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    wire = sum(1 for e in bm.edges if len(e.link_faces) == 0)
    loose = sum(1 for v in bm.verts if not v.link_edges)
    # vertices where two separate fans touch (non-manifold points)
    nmv = sum(1 for v in bm.verts if v.link_edges and not v.is_manifold and all(len(e.link_faces) == 2 for e in v.link_edges))
    # duplicate faces
    seen = set(); dup = 0
    for f in bm.faces:
        k = tuple(sorted(v.index for v in f.verts))
        if k in seen:
            dup += 1
        seen.add(k)
    # normals: edges whose two faces disagree in winding
    flipped = sum(1 for e in bm.edges if len(e.link_faces) == 2 and not e.is_contiguous)
    vol = bm.calc_volume(signed=True)
    # count shells and inward-facing (negative volume) shells
    bm.verts.ensure_lookup_table()
    seenv = set(); shells = 0; neg = 0
    for f0 in bm.faces:
        if f0.index in seenv:
            continue
        shells += 1
        st = [f0]; seenv.add(f0.index); v6 = 0.0
        while st:
            f = st.pop()
            vs = [v.co for v in f.verts]
            for i in range(1, len(vs) - 1):
                v6 += vs[0].dot(vs[i].cross(vs[i + 1]))
            for e in f.edges:
                for g in e.link_faces:
                    if g.index not in seenv:
                        seenv.add(g.index); st.append(g)
        if v6 <= 0:
            neg += 1
    r = {"verts": len(bm.verts), "faces": len(bm.faces), "boundary_edges": boundary, "nonmanifold_edges": nonman, "wire_edges": wire, "loose_verts": loose,
         "nonmanifold_verts": nmv, "duplicate_faces": dup, "inconsistent_normal_edges": flipped, "shells": shells, "inward_shells": neg, "volume_cm3": round(vol * 1e6, 2)}
    bm.free()
    return r


table = {}
for ob in sorted(coll().objects, key=lambda o: o.name):
    if ob.type == "MESH" and not ob.name.startswith(("tmp", "cut_", "cc_")):
        table[ob.name] = check_mesh(ob.data)
json.dump(table, open(SP + r"\n\watertight.json", "w"), indent=1)
KEYS = ["boundary_edges", "nonmanifold_edges", "wire_edges", "loose_verts", "nonmanifold_verts", "duplicate_faces", "inconsistent_normal_edges", "inward_shells"]
bad = 0
print("%-22s %7s %7s  bnd nonm wire loose nmv dup flip inward shells  vol_cm3" % ("object", "verts", "faces"))
for n, r in table.items():
    flag = any(r[k] for k in KEYS)
    bad += flag
    print("%-22s %7d %7d  %3d %4d %4d %5d %3d %3d %4d %6d %6d  %8.2f %s" % (n, r["verts"], r["faces"], r["boundary_edges"], r["nonmanifold_edges"], r["wire_edges"], r["loose_verts"],
          r["nonmanifold_verts"], r["duplicate_faces"], r["inconsistent_normal_edges"], r["inward_shells"], r["shells"], r["volume_cm3"], "<-- FIX" if flag else ""))
print("objects with problems:", bad, "of", len(table))
