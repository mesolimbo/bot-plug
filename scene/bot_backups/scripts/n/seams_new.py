# -- seams (open paths) --
def xy_path(pts, sign=-1):
    return polyline([solve_dir("z", x, y, sign) for x, y in pts], 0.012)


def _seg_x(a0, a1, b0, b1):
    """Intersection of two short arcs on the unit sphere (planar approximation about a0). Returns the point or None."""
    e1 = (a1 - a0)
    e1 -= a0 * e1.dot(a0)
    if e1.length < 1e-12:
        return None
    e1.normalize()
    e2 = a0.cross(e1)

    def uv(p):
        return (p - a0).dot(e1), (p - a0).dot(e2)
    (x1, y1), (x2, y2), (x3, y3), (x4, y4) = uv(a0), uv(a1), uv(b0), uv(b1)
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(den) < 1e-18:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / den
    if -1e-9 <= t <= 1 + 1e-9 and -1e-9 <= u <= 1 + 1e-9:
        return a0.lerp(a1, t).normalized()
    return None


def closest_on(B, p):
    best, bd = None, 1e9
    for b0, b1 in zip(B[:-1], B[1:]):
        d = b1 - b0
        t = max(0, min(1, (p - b0).dot(d) / max(d.length_squared, 1e-18)))
        q = b0 + d * t
        if (q - p).length < bd:
            bd, best = (q - p).length, q.normalized()
    return best, bd


def trim_to(A, B, end=True):
    """Make path A stop exactly on the centre line of path B (a T-junction): cut it where it crosses, or extend it to reach."""
    P = A if end else A[::-1]
    for i in range(len(P) - 1, max(0, len(P) - 30), -1):
        for b0, b1 in zip(B[:-1], B[1:]):
            if (b0 - P[i]).length > 0.05:
                continue
            X = _seg_x(P[i - 1], P[i], b0, b1)
            if X is not None:
                out = P[:i] + [X]
                if (out[-1] - out[-2]).length < 0.003 and len(out) > 2:
                    out = out[:-2] + [X]
                return out if end else out[::-1]
    q, _ = closest_on(B, P[-1])
    out = P + [q]
    return out if end else out[::-1]


def fork_cutter(A, B, name, sep_mm=2.5):
    """Where path A (starting on B) leaves B at a shallow angle, remove the knife-edge sliver between the two grooves
    so they blend into one: a thin triangle from the fork point out to where the panel between them is sep_mm wide."""
    Pf = A[0]
    need = 2 * HW + sep_mm / 1000 / RN
    j = min(range(len(B)), key=lambda k: (B[k] - Pf).length)
    best = None
    for dirn in (1, -1):
        Bs = B[j::dirn]
        if len(Bs) < 3 or len(A) < 3:
            continue
        dd = (Bs[min(4, len(Bs) - 1)] - A[min(4, len(A) - 1)]).length
        if best is None or dd < best[0]:
            best = (dd, Bs)
    Bs = best[1]
    la, lb = [Pf], [Pf]
    for k in range(1, min(len(A), len(Bs), 60)):
        la.append(A[k])
        lb.append(closest_on(Bs, A[k])[0])
        if (la[-1] - lb[-1]).length >= need:
            break
    loop = la + lb[:0:-1]
    c = Vector((0, 0, 0))
    for d in loop:
        c += d
    c.normalize()
    e1 = c.orthogonal().normalized()
    e2 = c.cross(e1)
    n = len(loop)
    area = sum(loop[i].dot(e1) * loop[(i + 1) % n].dot(e2) - loop[(i + 1) % n].dot(e1) * loop[i].dot(e2) for i in range(n))
    if area < 0:
        loop = loop[::-1]
    return cone_cutter(loop, name="cut_" + name)


# Clean, single-curvature curves fitted through the old (wobbly) painted lines; mirrored where the design is symmetric.
BELT_TOP = [(24.3, 35.3), (50, 34.4), (75, 31), (95, 26.2), (107, 22.3), (114.5, 21.0), (123, 22.6), (132, 25.6), (140.5, 27.5), (150, 27.6), (160, 25.6), (170, 20.9), (176, 16.6), (180, 13.4)]
SIDE = [(113.6, 21.2), (116.4, 17.6), (119.3, 11), (121, 0), (121, -12), (119.8, -21), (116.3, -29), (111.7, -35.5), (107, -42)]
UPPER_L = [(72.5, 47.5), (76, 42), (83, 38), (92, 34.5), (101, 30), (108.5, 25.6)]
STRIPE_TOP = [(119.2, 30.2), (130, 32.6), (140, 34.4), (152, 35.2), (160, 33.5), (168, 30.4), (174.5, 26.7), (180, 22.7)]
STRIPE_END = [(123.9, 21.9), (119.2, 30.2)]
CHEEK_LOW = [(120.2, -10.5), (121.6, -14.5), (123.5, -21), (127, -29), (131, -36), (136, -41.5), (140, -45), (145, -48), (152.5, -52), (160, -54), (170, -54.4), (180, -54.4)]
FLARE = [(139.6, -46.4), (141.5, -44.8), (149, -42.3), (156.5, -36), (161, -29.5), (164.0, -24.2), (165.6, -21.2)]
BIB = [(55.4, -10.6), (53.8, -17.5), (51, -24.5), (46.5, -33), (41.3, -42), (35, -51), (28.5, -59), (22, -65.3), (14.6, -70.3), (7, -70.9), (0, -71.0)]
WIN = [(149.7, 42.4), (149.5, 34.0)]
BELLY = [(-0.142, 0.041), (-0.058, 0.014), (0.0, 0.030), (0.073, 0.019), (0.105, 0.034), (0.166, 0.041)]
SEAMS = {
    "belt": S(BELT_TOP) + S(mir(BELT_TOP))[::-1][1:],
    "upperSideL": S(UPPER_L + SIDE), "sideR": S(mir(SIDE)),
    "arcR": S([(-57.5, 54.8), (-62, 52), (-66.5, 50.4), (-72, 48.8), (-82, 45), (-92, 43), (-101, 43), (-108, 44.5), (-113, 48), (-117, 53), (-119, 57.5)]),
    "vtip": Lp([(180, 13.4), (180, 8.5)]),
    "stripe": Lp(STRIPE_END)[:-1] + S(STRIPE_TOP) + S(mir(STRIPE_TOP))[::-1][1:] + Lp(mir(STRIPE_END)[::-1])[1:],
    "winL": Lp(WIN), "winR": Lp(mir(WIN)),
    "cheekLow": S(CHEEK_LOW + [(360 - lo, la) for lo, la in CHEEK_LOW[-2::-1]]),
    "flareL": S(FLARE), "flareR": S(mir(FLARE)),
    "bib": S(BIB + mir(BIB[-2::-1])),
    "belly": xy_path([(x, -y) for x, y in BELLY] + BELLY[::-1]),
    "trapFront": xy_path([(-0.058, -0.016), (-0.058, 0.016)]),
}
# T-junctions: (seam, which end, the seam it stops on). The first seam ends exactly on the centre line of the second.
TEES = [("sideR", "start", "belt"), ("stripe", "start", "belt"), ("stripe", "end", "belt"), ("winL", "end", "stripe"), ("winR", "end", "stripe"),
        ("cheekLow", "start", "upperSideL"), ("cheekLow", "end", "sideR"), ("flareL", "start", "cheekLow"), ("flareR", "start", "cheekLow"),
        ("belly", "start", "cheekLow"), ("belly", "end", "cheekLow"), ("trapFront", "start", "belly"), ("trapFront", "end", "belly")]
for a_, e_, b_ in TEES:
    SEAMS[a_] = trim_to(SEAMS[a_], SEAMS[b_], e_ == "end")
# shallow forks to blend: (seam leaving, reversed?, seam it leaves)
FORKS = [("cheekLow", False, "upperSideL"), ("cheekLow", True, "sideR")]
JUNCTION_PTS = {f"{a_}.{e_} on {b_}": (SEAMS[a_][-1] if e_ == "end" else SEAMS[a_][0]) for a_, e_, b_ in TEES}
JUNCTION_PTS["X upperSideL x belt"] = D(113.6, 21.2)
JUNCTION_PTS["V belt + vtip"] = D(180, 13.4)
JUNCTION_PTS["V stripe"] = D(180, 22.7)
JUNCTION_PTS["stripe corner L"] = D(119.2, 30.2)
JUNCTION_PTS["stripe corner R"] = D(-119.2, 30.2)
JUNCTION_PTS["bib x belly L"] = D(14.6, -70.3)
JUNCTION_PTS["bib x belly R"] = D(-14.6, -70.3)
JUNCTION_PTS["bib end L"] = D(55.4, -10.6)
JUNCTION_PTS["arcR start"] = D(-62, 52)
JUNCTION_PTS["upperSideL start"] = D(74, 45)
JUNCTION_PTS["belt start L"] = D(24.3, 35.3)
