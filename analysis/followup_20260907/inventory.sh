#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' 'FOLLOW-UP INVENTORY (read-only)'
date -u
find /home/user -maxdepth 1 -type f \( -iname '*cool*' -o -iname '*galil*' -o -iname '*shift*' -o -iname '*frame*' -o -iname '*queue*' \) -printf '%f\n' | sort   # one personal name pattern is left out of this copy
printf '%s\n' 'CODE STATUS'
for dir in /home/user/codes/athenapp /home/user/codes/athenapk /home/user/codes/arepo /home/user/codes/gizmo /home/user/codes/gadget4 /home/user/codes/gasoline; do
  printf '%s\n' "$dir"
  git -C "$dir" status --short --untracked-files=no 2>/dev/null | head -50 || true
done
printf '%s\n' 'CURRENT ATHENA INITIALIZERS'
sed -n '1,280p' /home/user/codes/athenapp/src/pgen/cloud_wind.cpp
printf '%s\n' 'COOLING AND FRAME-SHIFT FILE NAMES'
find /home/user/codes/athenapp/src/pgen /home/user/codes/athenapk/src/pgen /home/user/CloudCrushing -maxdepth 3 -type f \( -iname '*cool*' -o -iname '*shift*' -o -iname '*galil*' -o -iname '*manifest*' \) -printf '%p\n' | head -100
printf '%s\n' 'CURRENT LAUNCHER'
sed -n '1,240p' /home/user/verified_20260907/run_corrected_athpp.py
