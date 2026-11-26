p = "n/b5_socket.py"
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert a in s, a
    s = s.replace(a, b)


# The socket barrel stands proud of the curved housing plate all the way round, so the whole orange ring shows.
rep("XR = xs(SOCK_Z)\n", "XR = -0.2590                 # ring front = XR - 2.2 mm = -0.2612, proud of the plate everywhere (plate is at -0.2588 at the ring top)\n")
rep("FLOOR = -0.2385\n", '''BOSS_X = -0.2600            # flat sealing face of the socket barrel
boss = lathe([(0.0328, BOSS_X), (0.0405, BOSS_X), (0.0420, BOSS_X + 0.0015), (0.0420, -0.2280)], (0, 0, SOCK_Z), "X", 48)
new_obj("socket_boss", boss, "body", "dark", True, 30)
FLOOR = -0.2385
''')
rep("hole=(0.0, SOCK_Z, 0.0425)", "hole=(0.0, SOCK_Z, 0.0434)")
rep("HX, HZ = -0.2600, -0.0220", "HX, HZ = -0.2647, -0.0220")
rep("LID_IN, LID_OUT = -0.2580, -0.2630", "LID_IN, LID_OUT = -0.2627, -0.2677")
rep('new_obj("socket_plate", plate, "body", "dark", True, 30)', 'new_obj("socket_plate", plate, "body", "grey", True, 30)')
open(p, "w", encoding="utf-8").write(s)

p = "n/b0_common.py"
s = open(p, encoding="utf-8").read()
rep('ORDER = ["paint", "dark", "steel", "screen", "light", "stripe", "rubber"]', 'ORDER = ["paint", "dark", "steel", "screen", "light", "stripe", "rubber", "grey"]')
rep('        "rubber": mat("botn_rubber", (22, 22, 24), 0.8),', '        "rubber": mat("botn_rubber", (22, 22, 24), 0.8),\n        "grey": mat("botn_grey", (84, 82, 84), 0.5, 0.2),')
open(p, "w", encoding="utf-8").write(s)
print("patched 3")
