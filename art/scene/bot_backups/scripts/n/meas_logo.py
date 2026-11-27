import numpy as np
col = np.load(SP + r"\n\sph_col.npy"); H2, W2 = col.shape[:2]
lum = col.mean(axis=2)
yel = (col[..., 0] > 0.6) & (col[..., 2] < 0.3) & (col[..., 1] > 0.35)
dark = lum < 0.45
def region(mask, lon0, lon1, lat0, lat1, name):
    j0, j1 = int((90 - lat1) / 180 * H2), int((90 - lat0) / 180 * H2)
    i0, i1 = int((lon0 + 180) / 360 * W2), int((lon1 + 180) / 360 * W2)
    m = mask[j0:j1, i0:i1]
    rows = m.sum(axis=1); cols = m.sum(axis=0)
    print(name, "rows(lat: count) every 1 deg:")
    step = int(H2 / 180)
    print("  " + " ".join("%d:%d" % (round(90 - (j0 + k) * 180 / H2), rows[k:k + step].sum()) for k in range(0, len(rows), step)))
    print("  cols(lon: count): " + " ".join("%d:%d" % (round(-180 + (i0 + k) * 360 / W2), cols[k:k + step].sum()) for k in range(0, len(cols), step)))
region(dark, 30, 90, -15, 25, "BLACK front-left")
region(yel, -90, -30, -15, 25, "YELLOW front-right")
region(dark, -172, -122, -12, 24, "BLACK rear")
# flap bolt: orange pixels on old flap: scan rays from behind
old = bpy.data.objects["bot"]
bm = bmesh.new(); bm.from_mesh(old.data); bmesh.ops.triangulate(bm, faces=bm.faces)
bvh = BVHTree.FromBMesh(bm); uvl = bm.loops.layers.uv.active; bm.faces.ensure_lookup_table()
img = bpy.data.images["bot_baked"]; iw, ih = img.size
px = np.empty(iw * ih * 4, np.float32); img.pixels.foreach_get(px); px = px.reshape(ih, iw, 4)
ys, zs = [], []
from mathutils.geometry import barycentric_transform
for ky in range(-60, 61):
    for kz in range(-140, -20):
        y, z = ky * 0.001, kz * 0.001
        h = bvh.ray_cast(Vector((-1, y, z)), Vector((1, 0, 0)))
        if h[0] is None: continue
        f = bm.faces[h[2]]
        uv = barycentric_transform(h[0], *[v.co for v in f.verts], *[Vector((l[uvl].uv.x, l[uvl].uv.y, 0)) for l in f.loops])
        c = px[int(uv.y % 1 * ih) % ih, int(uv.x % 1 * iw) % iw]
        if c[0] > 0.7 and c[2] < 0.25 and 0.3 < c[1] < 0.75:
            ys.append(y); zs.append(z); xs_ = h[0].x
if ys: print("BOLT y %.3f..%.3f z %.3f..%.3f n %d" % (min(ys), max(ys), min(zs), max(zs), len(ys)))
bm.free()
