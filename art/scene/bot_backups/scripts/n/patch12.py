s = open("n/b5_socket.py", encoding="utf-8").read()
a = s.index("XR = -0.2590")
b = s.index("# Cloverleaf receptacle")
s = s[:a] + '''# Socket barrel and orange ring are ONE solid: the ring is the raised lip of the barrel, separated from the dark
# barrel face by a 0.6 mm groove, with the material boundary on edge loops. Nothing overlaps or shares a face with it.
BOSS_X = -0.2600            # flat sealing face of the barrel, proud of the curved plate all the way round
RING_F = BOSS_X - 0.0012    # front of the orange ring
BORE = 0.0328               # clear bore (the plug body is r 30, its glow ring r 31.5)
GROOVE = BOSS_X + 0.0008
prof = [(BORE, -0.2280), (BORE, GROOVE), (BORE, RING_F + 0.0008), (BORE + 0.0009, RING_F), (0.0357, RING_F), (0.0366, RING_F + 0.0008), (0.0366, GROOVE),
        (0.0372, GROOVE), (0.0372, BOSS_X), (0.0405, BOSS_X), (0.0420, BOSS_X + 0.0015), (0.0420, -0.2280)]
boss = lathe(prof, (0, 0, SOCK_Z), "X", 64, close=True)
set_mat(boss, "dark")


def _ring_face(f):
    c = f.calc_center_median()
    return math.hypot(c.y, c.z - SOCK_Z) < 0.0367 and c.x < GROOVE - 0.0001


set_mat(boss, "light", _ring_face)
new_obj("socket_boss", boss, "body", None, True, 30)
FLOOR = -0.2385
cup = lathe([(0, FLOOR), (BORE + 0.0006, FLOOR), (BORE + 0.0006, FLOOR + 0.0040), (0, FLOOR + 0.0040)], (0, 0, SOCK_Z), "X", 48)
new_obj("socket_cup", cup, "body", "rubber", True, 30)

''' + s[b:]
open("n/b5_socket.py", "w", encoding="utf-8").write(s)
s = open("n/b5_socket.py", encoding="utf-8").read()
assert "XR" not in s.split("# Cloverleaf receptacle")[1], "XR still used later"
print("patched 12")
