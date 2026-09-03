#!/bin/bash
# Level-5 Lagrangian runs, ONE AT A TIME.
# Each run.sh launches mpirun -np 8 and its header says it needs an otherwise
# idle machine. Four at once put 32 ranks and four ~300 MB ICs on a 27 GB box
# and the OOM killer took Arepo (rc=137). Serial costs nothing: one job already
# saturates the CPU.
#
# SAFETY: never clear an output directory that a live process is sitting in --
# an earlier version would have deleted a running job's snapshots.
set -u
CO=/home/kaan/codes
LOG=/mnt/c/Users/kaanb/CloudCrushing/results_A8/lag_serial.log
echo "=== LAGRANGIAN LEVEL 5, SERIAL $(date) ===" > "$LOG"
avail() { free -g | awk '/Mem:/{print $7}'; }
freegb() { df -BG --output=avail / 2>/dev/null | tail -1 | tr -dc '0-9'; }

busy() {  # is any running process cwd'd inside this directory?
  local d; d=$(readlink -f "$1")
  local p
  for p in $(pgrep -f "Arepo|GIZMO|gasoline|Gadget" 2>/dev/null); do
    [ "$(readlink -f /proc/$p/cwd 2>/dev/null)" = "$d" ] && return 0
  done
  return 1
}

count() { ls "$1"/output/snap*.hdf5 "$1"/output/snapshot*.hdf5 "$1"/*.0000?? 2>/dev/null | wc -l; }

one() { # label dir
  local label="$1" d="$2"
  [ -d "$d" ] && [ -x "$d/run.sh" ] || { echo "  SKIP $label" >> "$LOG"; return; }
  # let anything already running in this directory finish on its own
  local w=0
  while busy "$d"; do
    [ "$w" -eq 0 ] && echo "  WAIT $label (already running, letting it finish)" >> "$LOG"
    sleep 60; w=$((w+60)); [ "$w" -ge 43200 ] && break
  done
  local n; n=$(count "$d")
  [ "${n:-0}" -ge 90 ] && { echo "  HAVE $label ($n outputs)" >> "$LOG"; return; }
  while [ "$(avail)" -lt 10 ]; do sleep 60; done
  rm -rf "$d/output"; mkdir -p "$d/output"
  cd "$d" || return
  local t0=$(date +%s)
  timeout 43200 ./run.sh > launch.out 2>&1
  local rc=$?
  n=$(count "$d")
  echo "  $label rc=$rc wall=$(( $(date +%s)-t0 ))s outputs=$n ram=$(avail)GB disk=$(freegb)GB" >> "$LOG"
  [ "${n:-0}" -lt 90 ] && tail -3 run.out 2>/dev/null | sed 's/^/      /' >> "$LOG"
}

for chi in 10 100 1000; do
  one "Arepo     L5 chi=$chi" "$CO/arepo/runs/AREPO3D_L5_chi${chi}"
  one "GIZMO-MFM L5 chi=$chi" "$CO/gizmo/runs/GZ_L5_chi${chi}_mfm"
  one "GIZMO-MFV L5 chi=$chi" "$CO/gizmo/runs/GZ_L5_chi${chi}_mfv"
  one "Gasoline  L5 chi=$chi" "$CO/gasoline/runs/CW3D_L5_chi${chi}"
done
echo "=== DONE $(date) ===" >> "$LOG"
bash /home/kaan/publish_now.sh >> "$LOG" 2>&1
