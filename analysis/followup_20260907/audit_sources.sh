#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' 'GALILEAN SOURCES AND STATE'
find /home/kaan/codes/athenapp/src/pgen -maxdepth 1 -type f -iname '*cloud*' -printf '%f\n'
grep -R -n -E 'galilean|frame_shift|frame_velocity' /home/kaan/codes/athenapp/src/pgen/*cloud* || true
printf '%s\n' 'PARTICLE BUILD BOUNDARIES'
for root in arepo gizmo gadget4 gasoline; do
  printf '%s\n' "$root"
  find "/home/kaan/codes/$root" -maxdepth 3 -type f \( -name 'Config*.sh' -o -name 'Config.sh' -o -name '*3d*.param' \) -print | head -30
done
printf '%s\n' 'GRID AUDIT BOUNDARY INPUTS'
for kind in flash flashx enzo athw; do
  grep -i -E 'bound|bc\s*=|inflow|outflow|periodic|tracer|small|floor|cool' /home/kaan/ic_audit_20260907/grid_tests/${kind}_chi10/flash.par /home/kaan/ic_audit_20260907/grid_tests/${kind}_chi10/CloudWind.enzo /home/kaan/ic_audit_20260907/grid_tests/${kind}_chi10/athinput 2>/dev/null || true
done
printf '%s\n' 'ACTUAL PHYSICAL STORAGE'
df -B1 / /mnt/c
