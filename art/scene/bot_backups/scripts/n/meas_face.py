old = bpy.data.objects["bot"]
bpy.data.objects["bot_rig"].data.pose_position = "REST"
bm = bmesh.new(); bm.from_mesh(old.data)
bvh = BVHTree.FromBMesh(bm)
print("FACE x(rho) per angle (deg from +Y toward +Z), rho mm:", " ".join("%5d" % (k*5) for k in range(0, 45)))
for ang in range(0, 360, 30):
    a = math.radians(ang); row = []
    for k in range(0, 45):
        rho = k * 0.005
        h = bvh.ray_cast(Vector((1, rho*math.cos(a), 0.073 + rho*math.sin(a))), Vector((-1,0,0)))
        row.append("%5.1f" % (h[0].x*1000) if h[0] else "  -  ")
    print("a%3d" % ang, " ".join(row))
print("BACK x(y,z): rows z from 0.14 down to -0.14 step 0.01; cols y -0.07..0.07 step 0.01")
for kz in range(14, -15, -1):
    z = kz*0.01; row = []
    for ky in range(-7, 8):
        h = bvh.ray_cast(Vector((-1, ky*0.01, z)), Vector((1,0,0)))
        row.append("%6.1f" % (h[0].x*1000) if h[0] else "   -  ")
    print("z%5.2f" % z, " ".join(row))
print("UNDER z(x,y): rows x 0.2..-0.2 step .02; cols y -0.2..0.2 step 0.02 (body only)")
gid = old.vertex_groups["body"].index
dl = bm.verts.layers.deform.active
bm2 = bmesh.new(); bm2.from_mesh(old.data); dl2 = bm2.verts.layers.deform.active
rem = [v for v in bm2.verts if not (len(v[dl2]) and max(v[dl2].items(), key=lambda kv: kv[1])[0] == gid)]
bmesh.ops.delete(bm2, geom=rem, context="VERTS")
bvb = BVHTree.FromBMesh(bm2)
for kx in range(10, -11, -1):
    row = []
    for ky in range(-10, 11):
        h = bvb.ray_cast(Vector((kx*0.02, ky*0.02, -1)), Vector((0,0,1)))
        row.append("%5.0f" % (h[0].z*1000) if h[0] else "   - ")
    print("x%5.2f" % (kx*0.02), " ".join(row))
bm.free(); bm2.free()
