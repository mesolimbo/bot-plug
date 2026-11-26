#!/bin/bash
# Reduced bot (about half the triangles). Sources are in n_low/ (copies of n/ with the changes; n/ is untouched).
#   bash build_low.sh          builds the parts into collection "botr"
#   bash build_low.sh final    then joins them into bot_new (the full model stays, hidden, as bot_new_full) and removes "botr"
# n_low/label_full.npy is the panel label map of the full-resolution build; b1_shell.py needs it.
cd "/c/Users/mesol/AppData/Local/Temp/claude/3fec41d04d410712/f1237eee-dce1-4b40-88e6-7a7228eb5a6b/scratchpad"
P=n_low
cat $P/lib.py $P/b0_common.py $P/b0b_prims.py $P/b1_shell.py $P/dbg.py $P/b2_core.py $P/b3_top.py $P/b4_face.py $P/b5_socket.py $P/b6_legs.py > $P/_build.py
[ "$1" = "final" ] && cat $P/b9_final.py >> $P/_build.py
python -I bb.py $P/_build.py 2>&1 | grep -vE "^(probe|stage)"
rm -f $P/_build.py
