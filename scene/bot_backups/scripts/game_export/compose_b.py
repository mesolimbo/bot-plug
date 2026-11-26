"""Combine the bake passes: colour x (soft light, ambient occlusion, crevice grime), decals on top, glow left unshaded."""
import bpy
import numpy as np
G = "C:/Users/mesol/AppData/Local/Temp/claude/3fec41d04d410712/f1237eee-dce1-4b40-88e6-7a7228eb5a6b/scratchpad/g"
S = 4096
def load(n):
    im = bpy.data.images["bg_" + n]
    w, h = im.size
    a = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(a)
    a = a.reshape(h, w, 4)[:, :, :3]
    if w != S:
        a = a.repeat(S // w, 0).repeat(S // w, 1)
    return a
def soften(a, n=2):
    for _ in range(n):
        a = (a + np.roll(a, 1, 0) + np.roll(a, -1, 0) + np.roll(a, 1, 1) + np.roll(a, -1, 1)) / 5
    return a
ao, lit, emit = soften(load("ao")[..., 0]), soften(load("lit").mean(2)), load("emit").max(2)
dcol, da = load("dec_col"), load("dec_a")[..., 0]
da = da * 0  # decals ship as their own meshes now
dcol = np.clip(dcol / np.maximum(da, 0.02)[..., None], 0, 1)  # the decal colour comes back premultiplied by alpha
lit = np.clip(lit / max(np.percentile(lit[lit > 0.02], 95), 1e-3), 0, 1.15)
shade = ((0.7 + 0.3 * lit) * (0.3 + 0.7 * ao))[..., None]  # ambient occlusion carries most of the shading
grime = np.clip((0.82 - ao) / 0.5, 0, 1)[..., None] * 0.35
glow = np.clip(emit * 4, 0, 1)[..., None]
sc = bpy.context.scene
sc.render.image_settings.file_format = "JPEG"; sc.render.image_settings.quality = 90
sc.view_settings.view_transform = "Standard"
for kind in ("on", "off"):
    c = load("col_" + kind)
    c = c * (1 - da[..., None]) + dcol * da[..., None]
    f = c * (shade * (1 - da[..., None] * 0.75) + da[..., None] * 0.75)  # decals keep their ink colour
    gr = grime * (1 - da[..., None])
    f = f * (1 - gr) + f * np.array([0.80, 0.72, 0.60], np.float32) * gr
    f = f * (1 - glow) + c * glow
    name = "bot_game_" + kind
    im = bpy.data.images.get(name) or bpy.data.images.new(name, S, S, alpha=False)
    im.pixels.foreach_set(np.concatenate([np.clip(f, 0, 1), np.ones((S, S, 1), np.float32)], 2).ravel())
    im.filepath_raw = G + "/bot_" + kind + ".jpg"; im.file_format = "JPEG"
    im.save_render(im.filepath_raw)
    print(kind, "ok")
