import numpy as np
print("face loop top", lonlat(face_loop[24]), "side", lonlat(face_loop[0]), "bottom", lonlat(face_loop[72]))
print("top loop sample", [tuple(round(c,1) for c in lonlat(d)) for d in top_loop[::12]])
im = bpy.data.images.new("lab", FW, FH, alpha=False)
rng = np.random.RandomState(3); pal = rng.rand(64, 3); 
out = np.ones((FH, FW, 4), np.float32); out[..., :3] = np.where(LABEL[..., None] >= 0, pal[LABEL % 64], 0.0)
im.pixels.foreach_set(out[::-1].ravel()); im.filepath_raw = VD + "\label.png"; im.file_format = "PNG"; im.save(); bpy.data.images.remove(im)
sh = bpy.data.objects["shell"]
zs = [v.co.z for v in sh.data.vertices]
print("shell z range", min(zs), max(zs), len(zs))
