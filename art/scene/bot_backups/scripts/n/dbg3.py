print([tuple(round(c,1) for c in lonlat(face_loop[k])) for k in range(8, 41, 2)])
print([round(samp(R_CLOSE, D(0, la)), 4) for la in range(28, 46)])
print([round(samp(R_OLD, D(0, la)), 4) for la in range(28, 46)])
print([round(samp(R_OLD, D(15, la)), 4) for la in range(28, 46)])
