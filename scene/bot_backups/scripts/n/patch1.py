p = "n/b1_shell.py"
s = open(p, encoding="utf-8").read()
L = s.split("\n")
i0 = next(i for i, l in enumerate(L) if l.startswith("# -- seams (open paths)"))
i1 = next(i for i, l in enumerate(L) if l.startswith("SLOTS = {"))
new = open("n/seams_new.py", encoding="utf-8").read().rstrip("\n").split("\n")
s = "\n".join(L[:i0] + new + L[i1:])


def rep(a, b):
    global s
    assert a in s, a
    s = s.replace(a, b)


rep('''for name, path in SEAMS.items():
    boolean(shell, ribbon_cutter(path, HW, name="cut_" + name))
''', '''for name, path in SEAMS.items():
    boolean(shell, ribbon_cutter(path, HW, name="cut_" + name))
for a_, rev_, b_ in FORKS:
    boolean(shell, fork_cutter(SEAMS[a_][::-1] if rev_ else SEAMS[a_], SEAMS[b_], "fork_" + a_))
''')
rep('''for name, path in SEAMS.items():
    prev = None
    n_ = len(path)
    for i, d in enumerate(path):
''', '''for name, path in SEAMS.items():
    prev = None
    n_ = len(path)
    stops = [(e_, SEAMS[b_]) for a_, e_, b_ in TEES if a_ == name]
    for i, d in enumerate(path):
        # at a T-junction the floor stops at the wall of the groove it runs into
        if any(((e_ == "end" and i > n_ - 8) or (e_ == "start" and i < 8)) and closest_on(Bp, d)[1] < HW * 1.15 for e_, Bp in stops):
            prev = None
            continue
''')
rep("(290, 53.5), (296, 52.2), (300, 51.5)])[1:]", "(290, 53.6), (296, 52.4), (300, 51.5)])[1:]")
open(p, "w", encoding="utf-8").write(s)
print("patched")
