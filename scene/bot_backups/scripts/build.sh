#!/bin/bash
# usage: bash build.sh part1.py part2.py ...   (prepends n/lib.py and n/b0_common.py)
cd "/c/Users/mesol/AppData/Local/Temp/claude/3fec41d04d410712/f1237eee-dce1-4b40-88e6-7a7228eb5a6b/scratchpad"
cat n/lib.py n/b0_common.py "$@" > n/_build.py
python -I bb.py n/_build.py || { echo "(bridge error; waiting)"; sleep 5; python -I bb.py ping.py; }
