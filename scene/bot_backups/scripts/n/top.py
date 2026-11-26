S = {
 "t_top": ((0,0,2),(0,0,0.3),0.46),
 "t_f": ((1.2,0,1.6),(0,0,0.27),0.46),
 "t_b": ((-1.2,0,1.6),(0,0,0.27),0.46),
 "t_l": ((0,1.2,1.6),(0,0,0.27),0.46),
 "t_r": ((0,-1.2,1.6),(0,0,0.27),0.46),
 "t_flow": ((2,0,0.9),(0,0,0.27),0.46),
}
old_tex_shots(S, res=1000)
wb_shots(["bot"], {"g"+k: v for k, v in S.items()}, res=1000)
# profiles
old = bpy.data.objects["bot"]
bm = bmesh.new(); bm.from_mesh(old.data)
bvh = BVHTree.FromBMesh(bm)
for az in (0, 45, 90, 135, 180, 225, 270, 315):
    a = math.radians(az); row = []
    for k in range(0, 24):
        r = k * 0.01
        h = bvh.ray_cast(Vector((r*math.cos(a), r*math.sin(a), 1)), Vector((0,0,-1)))
        row.append("%.3f" % h[0].z if h[0] else "  -  ")
    print("az%3d" % az, " ".join(row))
bm.free()
