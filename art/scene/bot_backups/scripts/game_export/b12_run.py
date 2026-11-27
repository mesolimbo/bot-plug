LL, LR, LB = (88.0, 0.0, 0.200), (-88.0, 0.0, 0.200), (-145.5, -16.5, 0.125)  # rear: centred low on the right cheek
# ---- decals: conforming meshes 0.4 mm above the surface, alpha-blended, riding the body bone (bolt rides the dust cover) ----
# Run after b9_final.py (needs bot_new and bot_flap). Positions measured from the old model's texture.
import os, shutil
LOGOS = SP + r"\logos"
SCENE_DIR = r"C:\Users\mesol\OneDrive\Documents\Art\2026\Alan's Bot Plugs\art\scene"
for o in list(coll().objects):
    if o.name.startswith("decal_"):
        me = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.meshes.remove(me)


def decal_mat(name, src):
    dst = os.path.join(SCENE_DIR, "bot_" + src)
    if not os.path.exists(dst):
        shutil.copyfile(os.path.join(LOGOS, src), dst)
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    tex = nt.nodes.new("ShaderNodeTexImage")
    img = bpy.data.images.get("bot_" + src) or bpy.data.images.load(dst)
    img.name = "bot_" + src
    tex.image = img
    tex.extension = "CLIP"
    nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(tex.outputs["Alpha"], b.inputs["Alpha"])
    b.inputs["Roughness"].default_value = 0.55
    nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    try:
        m.surface_render_method = "BLENDED"
    except Exception:
        m.blend_method = "BLEND"
    return m, img.size[0] / img.size[1]


main = bpy.data.objects["bot_new"]
rig.data.pose_position = "REST"
bpy.context.view_layer.update()
bmm = bmesh.new()
bmm.from_mesh(main.data)
bvm = BVHTree.FromBMesh(bmm)
bmm.faces.ensure_lookup_table()
PAINT = ORDER.index("paint")


def parent_to_body(ob):
    pb = rig.pose.bones["body"]
    ob.parent = rig
    ob.parent_type = "BONE"
    ob.parent_bone = "body"
    ob.matrix_parent_inverse = (rig.matrix_world @ pb.matrix @ Matrix.Translation((0, pb.bone.length, 0))).inverted()


def shell_decal(name, src, lon, lat, width, nx=28, ny=16, lift=0.0004):
    m, aspect = decal_mat("botn_" + name, src)
    height = width / aspect
    c = D(lon, lat)
    u = (Vector((0, 0, 1)) - c * c.z).normalized()
    r = u.cross(c).normalized()
    R0 = (bvm.ray_cast(C + c * 0.6, -c)[0] - C).length
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    grid = []
    offpaint = 0
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            s, t = (i / nx - 0.5) * width, (j / ny - 0.5) * height
            vec = r * s + u * t
            rho = vec.length
            d = c if rho < 1e-9 else (c * math.cos(rho / R0) + vec / rho * math.sin(rho / R0))
            h = bvm.ray_cast(C + d * 0.6, -d)
            if bmm.faces[h[2]].material_index != PAINT:
                offpaint += 1
            row.append((bm.verts.new(h[0] + d * lift), (i / nx, j / ny)))
        grid.append(row)
    for j in range(ny):
        for i in range(nx):
            q = [grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]]
            f = bm.faces.new([a[0] for a in q])
            for l, a in zip(f.loops, q):
                l[uvl].uv = a[1]
            f.smooth = True
    bm.normal_update()
    if sum(f.normal.dot(c) for f in bm.faces) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    coll().objects.link(ob)
    parent_to_body(ob)
    print("%s: centre lon %.1f lat %.1f, %.0f x %.0f mm, grid points not on cream paint (seam/part crossings): %d of %d" % (name, lon, lat, width * 1000, height * 1000, offpaint, (nx + 1) * (ny + 1)))
    return ob


# old: black W + text at lon 38..74, lat -6..9.5 (173 x 75 mm); yellow W at lon -71..-41, lat -4.5..6.5 (144 x 53 mm);
# rear black W + text at lon -156..-126, lat -3..11.5 (140 x 68 mm). The new logos are less wide for their height, so each
# keeps the old logo's centre and is sized between the old width and the old height.
shell_decal("decal_abp_left", "decal_abp_black.png", LL[0], LL[1], LL[2])
shell_decal("decal_abp_right", "decal_abp_yellow.png", LR[0], LR[1], LR[2])
shell_decal("decal_abp_rear", "decal_abp_black.png", LB[0], LB[1], LB[2])
bmm.free()

# bolt on the dust cover (flap-local coordinates: closed pose, origin on the hinge axis)
HX_, HZ_, LID_IN_, LID_OUT_, SZ_ = -0.2647, -0.0220, -0.2627, -0.2677, 0.030
flap = bpy.data.objects["bot_flap"]
mb, asp = decal_mat("botn_decal_bolt", "decal_bolt.png")
BH = 0.040
BW = BH * asp


def flat_decal(name, x, vsign, nsign):
    """Quad on a lid face at local x. Image right is -Y (seen from behind the bot); image up is vsign * Z."""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    cz = SZ_ - HZ_
    pts = [((0, 0), (BW / 2, -BH / 2)), ((1, 0), (-BW / 2, -BH / 2)), ((1, 1), (-BW / 2, BH / 2)), ((0, 1), (BW / 2, BH / 2))]
    vs = [(bm.verts.new((x - HX_, y, cz + vsign * z)), uv) for uv, (y, z) in pts]
    f = bm.faces.new([a[0] for a in vs])
    for l, a in zip(f.loops, vs):
        l[uvl].uv = a[1]
    bm.normal_update()
    if f.normal.x * nsign < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mb)
    ob = bpy.data.objects.new(name, me)
    coll().objects.link(ob)
    ob.parent = flap
    return ob


flat_decal("decal_bolt_outer", LID_OUT_ - 0.0003, 1, -1)      # outer face: seen when the cover is closed
flat_decal("decal_bolt_inner", LID_IN_ + 0.0003, -1, 1)       # inner face: faces back while the cover hangs open (as on the old flap)
bpy.context.view_layer.update()
print("decals ok", [o.name for o in coll().objects])
