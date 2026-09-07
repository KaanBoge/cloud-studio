#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' 'FOLLOW-UP INVENTORY (read-only)'
date -u
find /home/kaan -maxdepth 1 -type f \( -iname '*cool*' -o -iname '*galil*' -o -iname '*shift*' -o -iname '*ryan*' -o -iname '*frame*' -o -iname '*queue*' \) -printf '%f\n' | sort
printf '%s\n' 'CODE STATUS'
for dir in /home/kaan/codes/athenapp /home/kaan/codes/athenapk /home/kaan/codes/arepo /home/kaan/codes/gizmo /home/kaan/codes/gadget4 /home/kaan/codes/gasoline; do
  printf '%s\n' "$dir"
  git -C "$dir" status --short --untracked-files=no 2>/dev/null | head -50 || true
done
printf '%s\n' 'CURRENT ATHENA INITIALIZERS'
sed -n '1,280p' /home/kaan/codes/athenapp/src/pgen/cloud_wind.cpp
printf '%s\n' 'COOLING AND FRAME-SHIFT FILE NAMES'
find /home/kaan/codes/athenapp/src/pgen /home/kaan/codes/athenapk/src/pgen /home/kaan/CloudCrushing -maxdepth 3 -type f \( -iname '*cool*' -o -iname '*shift*' -o -iname '*galil*' -o -iname '*manifest*' \) -printf '%p\n' | head -100
printf '%s\n' 'CURRENT LAUNCHER'
sed -n '1,240p' /home/kaan/verified_20260907/run_corrected_athpp.py
