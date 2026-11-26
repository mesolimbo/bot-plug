#!/bin/bash
# usage: ./run.sh n/script.py  (prepends n/lib.py)
cd "/c/Users/mesol/AppData/Local/Temp/claude/3fec41d04d410712/f1237eee-dce1-4b40-88e6-7a7228eb5a6b/scratchpad"
cat n/lib.py "$1" > n/_tmp.py && python -I bb.py n/_tmp.py
