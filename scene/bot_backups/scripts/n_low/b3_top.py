# ---- top assembly: dome, toothed ring, collar with lugs (all tilted 5.7 deg as measured), antenna -------
drop("dome", "top_ring", "ring_teeth", "collar", "lug*", "antenna*")
TOP_P = Vector((-0.020, 0.0, 0.335))
TOP_M = Matrix.Translation(TOP_P) @ Matrix.Rotation(math.radians(-5.7), 4, "Y")

# dome: a low puck with a crowned top and a crisp chamfered shoulder
dome = lathe([(0, 0.0195), (0.045, 0.0187), (0.066, 0.0160), (0.078, 0.0115), (0.0845, 0.0050), (0.0875, -0.0010), (0.0890, -0.0040), (0.0890, -0.0200), (0, -0.0200)], (0, 0, 0), "Z", 72)
new_obj("dome", xform(dome, TOP_M), "body", "paint", True, 25)

# dark toothed ring: ONE solid. The floor ring carries 22 evenly spaced teeth of equal height, with upright sides.
NT = 22
R_IN, R_OUT, T_IN, T_OUT = 0.0860, 0.1262, 0.0935, 0.1175
Z_FLOOR, Z_TOOTH, Z_BASE = -0.0190, -0.0150, -0.0260
st = []
eps = math.radians(0.12)
for k in range(NT):
    a0 = 2 * math.pi * k / NT
    a1 = a0 + 2 * math.pi / NT * 0.58
    for ang, h in ((a0 - eps, Z_FLOOR + 0.0002), (a0 + eps, Z_TOOTH), (a1 - eps, Z_TOOTH), (a1 + eps, Z_FLOOR + 0.0002)):
        c, s_ = math.cos(ang), math.sin(ang)
        st.append([Vector((r * c, r * s_, z)) for r, z in ((R_IN, Z_FLOOR), (T_IN, Z_FLOOR), (T_IN + 0.0008, h), (T_OUT - 0.0008, h), (T_OUT, Z_FLOOR), (R_OUT, Z_FLOOR), (R_OUT, Z_BASE), (R_IN, Z_BASE))])
ring = strip_solid(st, closed=True)
set_mat(ring, "dark")
set_mat(ring, "rubber", lambda f: all(v.co.z < Z_FLOOR + 0.0005 for v in f.verts))
new_obj("top_ring", xform(ring, TOP_M), "body", None, True, 30)

# collar: inner lip is a circle about the dome axis, outer edge an ellipse (thicker at the front, as on the old model)
COL_C, COL_RX, COL_RY = 0.012, 0.142, 0.153        # ellipse centre offset (local x) and semi-axes


def col_out(a):
    c, s = math.cos(a), math.sin(a)
    A = (c / COL_RX) ** 2 + (s / COL_RY) ** 2
    B = -2 * COL_C * c / COL_RX ** 2
    Cq = (COL_C / COL_RX) ** 2 - 1
    return (-B + math.sqrt(B * B - 4 * A * Cq)) / (2 * A)


def col_fun(a, r, h):
    if r >= 0.5:
        return col_out(a) + (r - 1.0), h
    return r, h


collar = lathe([(0.1250, -0.0230), (0.1250, -0.0135), (0.1265, -0.0120), (1.0 - 0.0015, -0.0290), (1.0, -0.0305), (1.0, -0.0560), (0.1250, -0.0560)], (0, 0, 0), "Z", 96, rfun=col_fun, close=True)
new_obj("collar", xform(collar, TOP_M), "body", "paint", True, 25)

# two lugs (bosses) on the left side
for i, (lx, ly, top, bot) in enumerate(((0.044, 0.120, -0.0050, -0.030), (-0.107, 0.103, -0.0245, -0.052))):
    lug = lathe([(0, top), (0.0125, top), (0.0145, top - 0.0015), (0.0180, top - 0.0045), (0.0190, top - 0.0060), (0.0190, bot), (0, bot)], (lx, ly, 0), "Z", 24)
    new_obj("lug%d" % i, xform(lug, TOP_M), "body", "paint", True, 25)

# antenna (vertical): boss on the rear-right shoulder, hex base, tapered mast with a collar and a tip
AX, AY = -0.0715, -0.1530
boss = lathe([(0.0, 0.3075), (0.0260, 0.3075), (0.0335, 0.3010), (0.0390, 0.2900), (0.0390, 0.2650), (0, 0.2650)], (AX, AY, 0), "Z", 32)
new_obj("antenna_boss", boss, "body", "paint", True, 25)
hexb = lathe([(0.0, 0.3190), (0.0150, 0.3190), (0.0185, 0.3165), (0.0185, 0.3070), (0, 0.3070)], (AX, AY, 0), "Z", 6)
new_obj("antenna_hex", hexb, "body", "steel", False)
mast = lathe([(0, 0.3180), (0.0125, 0.3180), (0.0105, 0.3300), (0.0085, 0.3480), (0.0064, 0.3680), (0.0058, 0.3900), (0.0052, 0.4500), (0.0048, 0.4780),
              (0.0062, 0.4790), (0.0062, 0.4890), (0.0048, 0.4900), (0.0040, 0.4955), (0.0022, 0.4985), (0.0, 0.4990)], (AX, AY, 0), "Z", 16)
new_obj("antenna_mast", mast, "body", "paint", True, 25)
print("top ok")
