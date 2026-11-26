"""Build the wall outlet from the chosen concept (outlet/gpt-a.png), the same way as the sign.

Run in a background Blender: blender -b --python outlet_build.py
Layout is taken in concept pixels and scaled by S. Every face is UV-projected straight from the front,
so the painted detail lines up with the geometry; sides and backs use plain dark metal. Materials:
  outlet_frame  frame, caps, bolts, nameplates, receptacle (concept texture, matte)
  outlet_light  light bar, status lamps, receptacle ring (concept texture, glowing)
  outlet_side   sides and backs (dark gunmetal)
Blender axes: X right, Z up, the outlet faces -Y (glTF +Z). The origin is the receptacle's centre on
the wall plane, which the game puts at SOCKET_POS.
"""
import math
import os

import bmesh
import bpy
import numpy as np

D = r"C:\Users\mesol\AppData\Local\Temp\claude\3fec41d04d410712\f1237eee-dce1-4b40-88e6-7a7228eb5a6b\scratchpad\outlet"
IMG = D + r"\outlet_tex.png"     # the concept with its receptacle shrunk to the bot socket's size (retex.py)
OUT_BLEND = r"C:\Users\mesol\OneDrive\Documents\Art\2026\Alan's Bot Plugs\scene\outlet.blend"
OUT_GLB = r"C:\Users\mesol\OneDrive\Documents\Art\2026\Alan's Bot Plugs\game\assets\outlet.glb"
IW, IH = 1024, 1536
S = 0.00036                # metres per concept pixel: the panel is 0.34 m wide, 0.49 m tall
CX, CY = 510, 785          # receptacle centre in the concept

# Silhouette from the concept: each row is one span, so the outline is its left and right ends.
rgb = np.frombuffer(open(D + r"\gpt-a.rgb", "rb").read(), np.uint8).reshape(IH, IW, 3).astype(int)
mask = np.abs(rgb - rgb[5, 5]).sum(2) > 40
rows = {}
for y in range(IH):
    xs = np.nonzero(mask[y])[0]
    if len(xs):
        rows[y] = (int(xs.min()), int(xs.max()) + 1)
Y0, Y1 = min(rows), max(rows) + 1


def rdp(pts, eps):
    if len(pts) < 3:
        return pts
    a, b = np.array(pts[0], float), np.array(pts[-1], float)
    ab = b - a
    n = np.hypot(*ab) or 1.0
    d = [abs(ab[0] * (p[1] - a[1]) - ab[1] * (p[0] - a[0])) / n for p in pts]
    i = int(np.argmax(d))
    if d[i] <= eps:
        return [pts[0], pts[-1]]
    return rdp(pts[:i + 1], eps)[:-1] + rdp(pts[i:], eps)


def side(y0, y1, right):
    """Silhouette edge from row y0 down to row y1, simplified."""
    pts = [(rows[y][1 if right else 0], y) for y in range(y0, y1)]
    return rdp(pts, 1.5)


def P(px, py):
    return (px - CX) * S, (CY - py) * S


# --- Fresh scene -----------------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
img = bpy.data.images.load(IMG)
img.name = "outlet_concept"


def material(name, emit=0.0, solid=None, rough=0.6, metal=0.3):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    if solid:
        bsdf.inputs["Base Color"].default_value = (*solid, 1)
    else:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = img
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        if emit > 0:
            nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
            bsdf.inputs["Emission Strength"].default_value = emit
    return m


ORDER = ["frame", "light", "side"]
MATS = {
    "frame": material("outlet_frame"),
    "light": material("outlet_light", emit=2.0, rough=0.3, metal=0.0),
    "side": material("outlet_side", solid=(0.055, 0.047, 0.05), rough=0.55, metal=0.6),
}
me = bpy.data.meshes.new("outlet")
ob = bpy.data.objects.new("outlet", me)
bpy.context.scene.collection.objects.link(ob)
for k in ORDER:
    me.materials.append(MATS[k])
bm = bmesh.new()


def face(verts, mat, toward):
    f = bm.faces.new(verts)
    f.normal_update()
    if (f.normal.y > 0) == (toward < 0):
        f.normal_flip()
    f.material_index = ORDER.index(mat)
    return f


def slab(poly_px, front, mat, back=0.0):
    """Extrude a front-view outline (concept pixels) from `front` m off the wall back to `back`."""
    pts = [P(*p) for p in poly_px]
    fv = [bm.verts.new((x, -front, z)) for x, z in pts]
    bv = [bm.verts.new((x, -back, z)) for x, z in pts]
    face(fv, mat, -1)
    if back > 0:
        face(bv, "side", 1)
    n = len(pts)
    area = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
    for i in range(n):
        j = (i + 1) % n
        s = bm.faces.new((fv[i], fv[j], bv[j], bv[i]))
        s.normal_update()
        # Outward is to the right of the edge for a counter-clockwise outline (x right, z up).
        ex, ez = pts[j][0] - pts[i][0], pts[j][1] - pts[i][1]
        out = (ez, -ex) if area > 0 else (-ez, ex)
        if s.normal.x * out[0] + s.normal.z * out[1] < 0:
            s.normal_flip()
        s.material_index = ORDER.index("side")
    return fv


def chamfer(x0, y0, x1, y1, c):
    return [(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)]


def circle(cx, cy, r, n):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy - r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def annulus(cx, cy, r0, r1, front, mat, back, n=64):
    """A ring standing off the surface: front face between r0 and r1, with inner and outer walls."""
    loops = []
    for r, z in ((r1, front), (r0, front), (r0, back), (r1, back)):
        loops.append([bm.verts.new((P(x, y)[0], -z, P(x, y)[1])) for x, y in circle(cx, cy, r, n)])
    for k in range(n):
        j = (k + 1) % n
        fr = bm.faces.new((loops[0][k], loops[0][j], loops[1][j], loops[1][k]))
        fr.normal_update()
        if fr.normal.y > 0:
            fr.normal_flip()
        fr.material_index = ORDER.index(mat)
        for a, b, sign in ((loops[1], loops[2], -1), (loops[3], loops[0], 1)):
            s = bm.faces.new((a[k], a[j], b[j], b[k]))
            s.normal_update()
            c = s.calc_center_median()
            cx0, cz0 = P(cx, cy)
            if (s.normal.x * (c.x - cx0) + s.normal.z * (c.z - cz0)) * sign < 0:
                s.normal_flip()
            s.material_index = ORDER.index("side")


# Recessed face: the whole silhouette, 2.5 cm off the wall.
outline = side(Y0, Y1, False) + [(x, y) for x, y in reversed(side(Y0, Y1, True))]
slab(outline, 0.025, "frame")
# Frame round it, 5 cm off the wall: top band with the cap, sides, and the bottom block.
FT, FB, FL, FR = 235, 1262, 130, 2 * CX - 130
slab(side(Y0, FT + 1, False) + [(x, y) for x, y in reversed(side(Y0, FT + 1, True))], 0.05, "frame", 0.025)
slab(side(FB, Y1, False) + [(x, y) for x, y in reversed(side(FB, Y1, True))], 0.05, "frame", 0.025)
slab(side(FT, FB + 1, False) + [(FL, FB), (FL, FT)], 0.05, "frame", 0.025)
slab([(FR, FT), (FR, FB)] + [(x, y) for x, y in reversed(side(FT, FB + 1, True))], 0.05, "frame", 0.025)
# Light bar in the top cap, bolts in the corners, nameplates.
slab(chamfer(280, 120, 2 * CX - 280, 173, 18), 0.056, "light", 0.045)
for bx, by in ((137, 230), (2 * CX - 137, 230), (137, 1297), (2 * CX - 137, 1297)):
    slab(circle(bx, by, 30, 6), 0.058, "frame", 0.045)
slab(chamfer(290, 359, 2 * CX - 290, 452, 8), 0.034, "frame", 0.02)
slab(chamfer(387, 1285, 2 * CX - 387, 1350, 6), 0.056, "frame", 0.045)
# Status lamps.
for lx in (397, 510, 623):
    slab(circle(lx, 277, 30, 24), 0.034, "light", 0.02)
# Receptacle, sized like the bot's socket (opening r 32.8 mm, glow ring to 46 mm): a housing, a socket disc the plug seats against (its back is 6.2 cm off the wall), and
# the glowing ring standing just proud of the disc.
slab(circle(CX, CY, 141.3, 64), 0.045, "frame", 0.02)
slab(circle(CX, CY, 109.8, 64), 0.058, "frame", 0.04)
annulus(CX, CY, 109.8, 128.9, 0.064, "light", 0.04)

# Front projection UVs: concept pixel = position.
uv = bm.loops.layers.uv.new("UVMap")
for f in bm.faces:
    for loop in f.loops:
        x, _, z = loop.vert.co
        loop[uv].uv = ((x / S + CX) / IW, 1 - (CY - z / S) / IH)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
bm.to_mesh(me)
bm.free()
me.update()

cam = bpy.data.objects.new("outlet_cam", bpy.data.cameras.new("outlet_cam"))
bpy.context.scene.collection.objects.link(cam)
cam.location = (0, -1.2, 0.03)
cam.rotation_euler = (1.5708, 0, 0)
bpy.context.scene.camera = cam
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
for o in bpy.context.scene.objects:
    o.select_set(o is ob)
bpy.context.view_layer.objects.active = ob
bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format="GLB", use_selection=True, export_yup=True,
                          export_image_format="JPEG", export_jpeg_quality=92, export_materials="EXPORT")
print("faces", len(me.polygons), "size", [round(v, 3) for v in ob.dimensions], "glb", os.path.getsize(OUT_GLB))
