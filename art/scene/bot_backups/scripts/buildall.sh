#!/bin/bash
cd "/c/Users/mesol/AppData/Local/Temp/claude/3fec41d04d410712/f1237eee-dce1-4b40-88e6-7a7228eb5a6b/scratchpad"
bash build.sh n/b0b_prims.py n/b1_shell.py n/dbg.py n/b2_core.py n/b3_top.py n/b4_face.py n/b5_socket.py n/b6_legs.py "$@" 2>&1 | grep -vE "^(probe|stage)"
