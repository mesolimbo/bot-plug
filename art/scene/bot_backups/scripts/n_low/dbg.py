import numpy as np
print(len(islands), keep_ids, [round(a*RN*RN*1e4,1) for a in areas])
for lo, la, nm in ((0,37,"brow"),(50,42,"leafL"),(100,40,"LR"),(165,38,"rearcollar"),(-100,50,"RR"),(-60,42,"RF"),(140,0,"cheekL"),(-140,0,"cheekR"),(80,0,"sideL"),(-80,0,"sideR"),(0,-55,"chin"),(180,-45,"dark"),(150,31.5,"stripe"),(100,28,"sliverL")):
    k = label_at(lo, la)
    print(nm, k, (LABEL == k).sum() if k >= 0 else None, round(samp(FIELD[k], D(lo, la)), 4) if k >= 0 else None, round(samp(R_OLD, D(lo, la)), 4))
