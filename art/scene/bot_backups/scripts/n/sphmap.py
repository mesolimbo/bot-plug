import numpy as np, time
t0 = time.time()
C = Vector((0, 0, 0.08))
W, H = 1600, 800
old = bpy.data.objects["bot"]
bpy.data.objects["bot_rig"].data.pose_position = "REST"
bpy.context.view_layer.update()
bm = bmesh.new(); bm.from_mesh(old.data)
bmesh.ops.triangulate(bm, faces=bm.faces)
uvl = bm.loops.layers.uv.active
dl = bm.verts.layers.deform.active
gid = old.vertex_groups["body"].index
bm.verts.ensure_lookup_table()
verts = [v.co.copy() for v in bm.verts]
isbody = [max(v[dl].items(), key=lambda kv: kv[1])[0] == gid if len(v[dl]) else False for v in bm.verts]
tris, tuv = [], []
for f in bm.faces:
    if all(isbody[v.index] for v in f.verts):
        tris.append([v.index for v in f.verts])
        tuv.append([tuple(l[uvl].uv) for l in f.loops])
bvh = BVHTree.FromPolygons(verts, tris)
bm.free()
V = np.array(verts); T = np.array(tris); TUV = np.array(tuv)
rad = np.zeros((H, W), np.float32); fidx = np.full((H, W), -1, np.int64); hp = np.zeros((H, W, 3))
for j in range(H):
    lat = math.pi * (0.5 - (j + 0.5) / H)
    cz, sz = math.cos(lat), math.sin(lat)
    for i in range(W):
        lon = 2 * math.pi * ((i + 0.5) / W - 0.5)
        d = Vector((cz * math.cos(lon), cz * math.sin(lon), sz))
        hit = bvh.ray_cast(C + d, -d)
        if hit[0] is not None:
            rad[j, i] = 1.0 - hit[3]; fidx[j, i] = hit[2]; hp[j, i] = hit[0]
ok = fidx >= 0
f = np.where(ok, fidx, 0)
a, b, c = V[T[f, 0]], V[T[f, 1]], V[T[f, 2]]
v0, v1, v2 = b - a, c - a, hp - a
d00 = (v0 * v0).sum(-1); d01 = (v0 * v1).sum(-1); d11 = (v1 * v1).sum(-1); d20 = (v2 * v0).sum(-1); d21 = (v2 * v1).sum(-1)
den = d00 * d11 - d01 * d01 + 1e-20
w1 = (d11 * d20 - d01 * d21) / den; w2 = (d00 * d21 - d01 * d20) / den; w0 = 1 - w1 - w2
uv = w0[..., None] * TUV[f, 0] + w1[..., None] * TUV[f, 1] + w2[..., None] * TUV[f, 2]
img = bpy.data.images["bot_baked"]
iw, ih = img.size
px = np.empty(iw * ih * 4, np.float32); img.pixels.foreach_get(px); px = px.reshape(ih, iw, 4)
ix = np.clip((uv[..., 0] % 1.0 * iw).astype(int), 0, iw - 1); iy = np.clip((uv[..., 1] % 1.0 * ih).astype(int), 0, ih - 1)
col = px[iy, ix]; col[~ok] = (1, 0, 1, 1)
np.save(SP + r"\n\sph_rad.npy", rad); np.save(SP + r"\n\sph_col.npy", col[..., :3].astype(np.float32))
def save(arr, name):
    im = bpy.data.images.new("tmp_sph", W, H, alpha=False)
    out = np.ones((H, W, 4), np.float32); out[..., :3] = arr; out = out[::-1]
    im.pixels.foreach_set(out.ravel()); im.filepath_raw = VD + "\\" + name; im.file_format = "PNG"; im.save(); bpy.data.images.remove(im)
save(col[..., :3], "sph_col.png")
g = np.clip((rad - 0.20) / 0.10, 0, 1); save(np.stack([g, g, g], -1), "sph_rad.png")
print("done", time.time() - t0, ok.mean(), rad[ok].min(), rad[ok].max())
