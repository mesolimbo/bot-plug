old = bpy.data.objects["bot"]
AX, AY = -0.073, -0.153
rows = {}
for v in old.data.vertices:
    p = v.co
    r = math.hypot(p.x - AX, p.y - AY)
    if p.z > 0.27 and r < 0.06:
        k = round(p.z / 0.005)
        a = rows.setdefault(k, [0, 0, 0, 0])
        a[0] = max(a[0], r); a[1] += 1; a[2] += p.x; a[3] += p.y
for k in sorted(rows):
    a = rows[k]
    print("z %.3f rmax %.4f n %d  c (%.4f, %.4f)" % (k * 0.005, a[0], a[1], a[2] / a[1], a[3] / a[1]))
