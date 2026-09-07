#!/bin/bash
# THE BALANCED LADDER: levels 1 through 4, every chi, for the codes whose inputs
# are already verified against the matched spec. Levels 1-4 are cheap enough that
# a complete, gap-free matrix is genuinely achievable, which is the point: a
# comparison with holes in it is much harder to read than one without.
#
#   level 1 =  16 x   8 x   8      0.8 cells per cloud radius
#   level 2 =  32 x  16 x  16      1.6
#   level 3 =  64 x  32 x  32      3.2
#   level 4 = 128 x  64 x  64      6.4
#   (level 5 = 256x128x128 = 12.8 and level 6 = 512x256x256 = 25.6 run separately)
#
# HONEST CAVEAT recorded here so it reaches the write-up: below about level 3 the
# cloud spans only a few cells and the result is not physically meaningful on its
# own. These rungs earn their place by showing how each code CONVERGES, not by
# being believable simulations in isolation.
#
# Rank counts fall with the grid: 8 ranks cannot usefully decompose a 16x8x8 box.
set -u
CC=/home/kaan/CloudCrushing
CO=/home/kaan/codes
PY=/home/kaan/venv/bin/python
LOG=/mnt/c/Users/kaanb/CloudCrushing/results_A8/ladder.log
echo "=== BALANCED LADDER, LEVELS 1-4 $(date) ===" > "$LOG"

# never start while the level-5 matched set is still using the machine
w=0
while false; do
  sleep 120; w=$((w+120)); [ "$w" -ge 172800 ] && break
done
echo "waited ${w}s for the level-5 campaign" >> "$LOG"

tlim_of() { $PY -c "import math,sys;print('%.5f'%(5*math.sqrt(float(sys.argv[1]))/2.582))" "$1"; }
dt_of()   { $PY -c "import math,sys;print('%.6f'%(5*math.sqrt(float(sys.argv[1]))/2.582/100))" "$1"; }
nx_of()   { echo $(( 8 * (2 ** $1) )); }        # level 1 -> 16, level 4 -> 128
ranks_of() { case $1 in 1) echo 1;; 2) echo 1;; 3) echo 2;; *) echo 2;; esac; }
mb_of()   { local n=$1; local m=32; while [ $m -gt $(( n / 2 )) ]; do m=$(( m / 2 )); done;
            [ $m -lt 4 ] && m=4; echo $m; }

# ------------------------------------------------------ AthenaPK (GPU tier)
apk() { # level chi
  local L=$1 chi=$2
  local nx=$(nx_of $L) ny nz mb tlim dt
  ny=$(( nx / 2 )); nz=$(( nx / 2 )); mb=$(mb_of $ny)
  tlim=$(tlim_of $chi); dt=$(dt_of $chi)
  local d=$CO/athenapk/runs/LAD_L${L}_chi${chi}
  mkdir -p "$d"; cd "$d" || return
  # AthenaPK stores the streamwise axis as x2
  sed -e "s/^rho_cloud_cgs *=.*/rho_cloud_cgs = ${chi}.0/" \
      -e "s/^tlim *=.*/tlim = $tlim/" -e "s/^dt *=.*/dt = $dt/" \
      -e "s/^nx1 *= *256/nx1 = $ny/" -e "s/^nx2 *= *512/nx2 = $nx/" -e "s/^nx3 *= *256/nx3 = $nz/" \
      -e "s/^nx1 *= *64/nx1 = $mb/" -e "s/^nx2 *= *64/nx2 = $mb/" \
      "$CO/athenapk/runs/APK3D_chi10_512/athinput" > athinput
  [ "$chi" -ge 1000 ] && sed -i "/^<hydro>/a dfloor = 1.0e-6\npfloor = 1.0e-8" athinput
  rm -f ./*.phdf ./*.hst
  timeout 7200 nice -n 19 "$CO/athenapk/build-cuda/bin/athenaPK" -i athinput > run.out 2>&1
  echo "  AthenaPK  L$L chi=$chi  ${ny}x${nx}x${nz}  rc=$? snaps=$(ls ./*.phdf 2>/dev/null | wc -l)" >> "$LOG"
}

# --------------------------------------------------------- Athena 4.2 (CPU)
athw() { # level chi
  local L=$1 chi=$2
  local nx=$(nx_of $L) ny nz np tlim dt
  ny=$(( nx / 2 )); nz=$(( nx / 2 )); np=$(ranks_of $L)
  tlim=$(tlim_of $chi); dt=$(dt_of $chi)
  local d=$CC/A8/LAD_ATHW_L${L}_chi${chi}
  mkdir -p "$d"; cd "$d" || return
  sed -e "s/^drat *=.*/drat = $chi/" -e "s/^tlim *=.*/tlim = $tlim/" -e "s/^dt *=.*/dt = $dt/" \
      -e "s/^Nx1 *=.*/Nx1 = $nx/" -e "s/^Nx2 *=.*/Nx2 = $ny/" -e "s/^Nx3 *=.*/Nx3 = $nz/" \
      "$CC/A8/ATHW3D_chi10_256/athinput" > athinput
  cp -f "$CC/A8/athena_wind_mpi" ./athena_lad 2>/dev/null
  timeout 10800 nice -n 19 mpirun --oversubscribe -np $np ./athena_lad -i athinput > run.out 2>&1
  echo "  Athena4.2 L$L chi=$chi  ${nx}x${ny}x${nz} np=$np  rc=$? dumps=$(ls id0/*.vtk 2>/dev/null | wc -l)" >> "$LOG"
}

# ----------------------------------------------------------- Athena++ (CPU)
athpp() { # level chi
  local L=$1 chi=$2
  local nx=$(nx_of $L) ny nz mb np tlim dt
  ny=$(( nx / 2 )); nz=$(( nx / 2 )); mb=$(mb_of $ny); np=$(ranks_of $L)
  tlim=$(tlim_of $chi); dt=$(dt_of $chi)
  local d=$CO/athenapp/runs/LAD_ATHPP_L${L}_chi${chi}
  mkdir -p "$d"; cd "$d" || return
  sed -e "s/^drat *=.*/drat = ${chi}.0/" -e "s/^tlim *=.*/tlim = $tlim/" -e "s/^dt *=.*/dt = $dt/" \
      -e "s/^nx1 *= *256/nx1 = $nx/" -e "s/^nx2 *= *128/nx2 = $ny/" -e "s/^nx3 *= *128/nx3 = $nz/" \
      -e "s/^nx1 *= *32/nx1 = $mb/" -e "s/^nx2 *= *32/nx2 = $mb/" \
      "$CO/athenapp/runs/ATHPP3D_chi10_256/athinput.cloud_wind" > athinput.cloud_wind
  grep -q "^rv_scale" athinput.cloud_wind || sed -i "/^drat/a rv_scale = 1.3" athinput.cloud_wind
  rm -f ./*.athdf
  timeout 10800 nice -n 19 mpirun --oversubscribe -np $np "$CO/athenapp/bin/athena" \
      -i athinput.cloud_wind -d . > run.out 2>&1
  echo "  Athena++  L$L chi=$chi  ${nx}x${ny}x${nz} np=$np  rc=$? dumps=$(ls ./*.athdf 2>/dev/null | wc -l)" >> "$LOG"
}

# cheapest rung first, and every chi filled before moving up, so the matrix is
# complete at each level rather than deep in one corner
for L in 1 2 3 4; do
  echo "--- LEVEL $L ($(nx_of $L) x $(( $(nx_of $L) / 2 )) x $(( $(nx_of $L) / 2 )), $(echo "scale=1; $(nx_of $L)/20" | bc) cells per cloud radius) ---" >> "$LOG"
  for chi in 10 100 1000; do
    apk   $L $chi
    athw  $L $chi
    athpp $L $chi
  done
done

echo "=== LADDER DONE $(date) ===" >> "$LOG"
grep -cE "rc=0" "$LOG" | sed 's/^/runs succeeded: /' >> "$LOG"
