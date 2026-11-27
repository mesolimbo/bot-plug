old = bpy.data.objects["bot"]
rig = bpy.data.objects["bot_rig"]
rig.data.pose_position = "REST"
gi = {g.name: g.index for g in old.vertex_groups}
dom = {}
for v in old.data.vertices:
    b = max(v.groups, key=lambda g: g.weight) if v.groups else None
    dom[v.index] = b.group if b else -1
H = {n: rig.data.bones[n].head_local.copy() for n in ("thigh.L", "shin.L", "foot.L")}
TL = rig.data.bones["foot.L"].tail_local.copy()


def frame(name, a, b):
    u = (b - a); u.y = 0; L = u.length; u.normalize()
    n = Vector((-u.z, 0, u.x))
    pts = [old.data.vertices[i].co for i, g in dom.items() if g == gi[name]]
    print(name, "len %.3f" % L, "nverts", len(pts), "u", tuple(round(c, 3) for c in u))
    rows = {}
    for p in pts:
        d = p - a
        s, t, w = d.dot(u), d.dot(n), p.y - a.y
        k = math.floor(s / 0.01)
        r = rows.setdefault(k, [1e9, -1e9, 1e9, -1e9, 0])
        r[0] = min(r[0], t); r[1] = max(r[1], t); r[2] = min(r[2], w); r[3] = max(r[3], w); r[4] += 1
    for k in sorted(rows):
        r = rows[k]
        print("  s %5.2f..: t %6.1f..%6.1f  w %6.1f..%6.1f  n=%d" % (k * 0.01, r[0] * 1000, r[1] * 1000, r[2] * 1000, r[3] * 1000, r[4]))


frame("thigh.L", H["thigh.L"], H["shin.L"])
frame("shin.L", H["shin.L"], H["foot.L"])
# foot: world x bins
pts = [old.data.vertices[i].co for i, g in dom.items() if g == gi["foot.L"]]
rows = {}
for p in pts:
    k = math.floor(p.x / 0.01)
    r = rows.setdefault(k, [1e9, -1e9, 1e9, -1e9, 0])
    r[0] = min(r[0], p.z); r[1] = max(r[1], p.z); r[2] = min(r[2], p.y - 0.1033); r[3] = max(r[3], p.y - 0.1033); r[4] += 1
print("foot.L by x")
for k in sorted(rows):
    r = rows[k]
    print("  x %5.2f..: z %6.1f..%6.1f  w %6.1f..%6.1f n=%d" % (k * 0.01, r[0] * 1000, r[1] * 1000, r[2] * 1000, r[3] * 1000, r[4]))
# w-profile of wheels: for verts within 0.065 of each joint centre (any leg group), radial extent per w bin
for jn in ("thigh.L", "shin.L", "foot.L"):
    c = H[jn]
    rows = {}
    for i, g in dom.items():
        if g in (gi["thigh.L"], gi["shin.L"], gi["foot.L"], gi["body"]):
            p = old.data.vertices[i].co
            rr = math.hypot(p.x - c.x, p.z - c.z)
            if rr < 0.07 and abs(p.y - c.y) < 0.08:
                k = math.floor((p.y - c.y) / 0.005)
                r = rows.setdefault(k, [0, 0])
                r[0] = max(r[0], rr); r[1] += 1
    print("joint", jn, " ".join("%d:%.0f(%d)" % (k * 5, rows[k][0] * 1000, rows[k][1]) for k in sorted(rows)))
