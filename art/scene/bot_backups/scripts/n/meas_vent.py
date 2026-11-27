import numpy as np
old = bpy.data.objects["bot"]
bm = bmesh.new(); bm.from_mesh(old.data)
bvh = BVHTree.FromBMesh(bm)
col = np.load(SP + r"\n\sph_col.npy"); Hc, Wc = col.shape[:2]


def colat(p):
    d = (p - C).normalized(); lo, la = lonlat(d)
    return col[int((90 - la) / 180 * Hc) % Hc, int((lo + 180) / 360 * Wc) % Wc]


def scan(label, x, y0, y1, step=0.001):
    print(label, "x=%.3f: y(mm): z(mm) lum" % x)
    row = []
    y = y0
    while y <= y1 + 1e-9:
        h = bvh.ray_cast(Vector((x, y, 1)), Vector((0, 0, -1)))
        if h[0]:
            c = colat(h[0]); row.append("%d:%.1f/%.2f" % (round(y * 1000), h[0].z * 1000, float(c.mean())))
        y += step
    print(" ".join(row))


def scanx(label, y, x0, x1, step=0.002):
    print(label, "y=%.3f: x(mm): z(mm) lum" % y)
    row = []
    x = x0
    while x <= x1 + 1e-9:
        h = bvh.ray_cast(Vector((x, y, 1)), Vector((0, 0, -1)))
        if h[0]:
            c = colat(h[0]); row.append("%d:%.1f/%.2f" % (round(x * 1000), h[0].z * 1000, float(c.mean())))
        x += step
    print(" ".join(row))


scan("FRONT grille across", 0.165, -0.11, 0.11, 0.002)
scan("FRONT grille across", 0.185, -0.11, 0.11, 0.002)
scan("REAR grille across", -0.165, -0.11, 0.11, 0.002)
scanx("FRONT grille radial (between ribs)", 0.0, 0.125, 0.21)
scanx("FRONT grille radial (on rib)", -0.033, 0.125, 0.21)
scanx("REAR grille radial (between ribs)", 0.028, -0.20, -0.135)
scanx("REAR grille radial (on rib)", 0.0, -0.20, -0.135)
scanx("ring radial front", 0.0, 0.06, 0.125, 0.001)
scan("ring radial side", -0.02, 0.08, 0.135, 0.001)
bm.free()
S_ = {"vf": ((0.9, 0, 1.2), (0.165, 0, 0.275), 0.26), "vr": ((-0.9, 0, 1.2), (-0.165, 0, 0.27), 0.26), "vt": ((0, 0, 2), (-0.02, 0, 0.3), 0.32),
      "vfe": ((2, 0, 0.6), (0.165, 0, 0.275), 0.26), "vre": ((-2, 0, 0.6), (-0.165, 0, 0.27), 0.26), "vs": ((0.3, 1.2, 1.4), (-0.03, 0.16, 0.29), 0.26)}
old_tex_shots(S_, res=1000)
wb_shots(["bot"], {"g" + k: v for k, v in S_.items()}, res=1000)
print("vent shots")
