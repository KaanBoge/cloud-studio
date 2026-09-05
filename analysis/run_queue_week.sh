#!/bin/bash
# ============================================================================
# WEEK QUEUE: everything on Ryan's list that can run without supervision.
#
# Ordered so the highest value lands first, because a queue that dies on
# Thursday should still have delivered the Mach study.
#
#   A  backfill the exports that block the disk sweep, then sweep
#   B  Mach 0.5 / 1.5 / 5 on AthenaPK (GPU, minutes per run) at levels 4 and 5
#   D  radiative cooling, Townsend 2009 exact integration on a Schure table,
#      which AthenaPK already has compiled in
#   C  Mach 0.5 / 1.5 / 5 on Athena++, Athena 4.2 and Enzo at level 4
#   E  finish level 5 for the Lagrangian codes, serial
#   F  regenerate every figure and publish
#
# DISK IS THE BINDING CONSTRAINT. The overnight run died at 0 bytes free, so:
#   - new runs write 21 snapshots, not 101 (every 0.25 t_cc). That is still a
#     usable mass-evolution curve and still gives the final frame, at a fifth
#     of the disk.
#   - every run is exported, diagnosed, then stripped to its last snapshot
#     before the next one starts.
#   - nothing starts below the stated free-space floor; below it the queue
#     sweeps, and if still low it skips that cell and says so rather than
#     dying mid-run.
# ============================================================================
set -u
PY=/home/kaan/venv/bin/python
CO=/home/kaan/codes
A8=/home/kaan/CloudCrushing/A8
STORE=/mnt/c/Users/kaanb/cloud-frames-repo
LOG=/mnt/c/Users/kaanb/CloudCrushing/results_A8/week_queue.log
FIG=/mnt/c/Users/kaanb/CloudCrushing/figures
SWEEP=/home/kaan/sweep_gap.sh
CS=1.290994448735806
COOLTBL=$CO/athenapk/inputs/cooling_tables/schure.cooling_1.0Z
APK=$CO/athenapk/build-cuda/bin/athenaPK

mkdir -p "$FIG"
echo "=== WEEK QUEUE $(date) ===" > "$LOG"
say() { echo "$*" >> "$LOG"; }

(setsid nohup bash /home/kaan/oom_priority.sh >/dev/null 2>&1 &) 2>/dev/null

freegb() { df -BG --output=avail / 2>/dev/null | tail -1 | tr -dc 0-9; }
availram() { free -g | awk '/Mem:/{print $7}'; }

need_disk() {
  local want=$1
  [ "$(freegb)" -ge "$want" ] && return 0
  say "  disk $(freegb)GB below ${want}GB, sweeping"
  [ -x "$SWEEP" ] && bash "$SWEEP" >/dev/null 2>&1
  [ "$(freegb)" -ge "$want" ]
}

harvest() {
  local tag=$1 kind=$2 chi=$3 tcc=$4 dir=$5 glob=$6
  local files n d last f
  files=$(ls -d $dir/$glob 2>/dev/null | sort)
  n=$(echo "$files" | grep -c .)
  if [ "${n:-0}" -lt 5 ]; then say "    nothing to harvest for $tag"; return 1; fi
  rm -rf "${STORE:?}/$tag"
  nice -n 19 $PY /home/kaan/dense_export.py "$tag" "$kind" "$chi" "$STORE" $files >> "$LOG" 2>&1
  nice -n 19 $PY /home/kaan/diagnostics.py "$tag" "$kind" "$chi" "$tcc" $files >> "$LOG" 2>&1
  d=$(ls "$STORE/$tag"/f*.bin 2>/dev/null | wc -l)
  last=$(echo "$files" | tail -1)
  for f in $files; do
    if [ "$f" != "$last" ]; then rm -rf "$f"; fi
  done
  say "    $tag harvested: $n raw into $d frames, raw stripped, free=$(freegb)GB"
}

publish() { bash /home/kaan/publish_now.sh >> "$LOG" 2>&1; }

# ---------------------------------------------------------------- A: unblock
say ""
say "--- A: backfill blocked exports, then sweep ---"
for chi in 10 100 1000; do
  d=$CO/ramses/runs/RAM3D_chi${chi}
  if [ -d "$d" ]; then
    n=$(ls -d $d/output_* 2>/dev/null | wc -l)
    have=$(ls $STORE/ramses_L5_chi${chi}/f*.bin 2>/dev/null | wc -l)
    if [ "${n:-0}" -gt "${have:-0}" ]; then
      rm -rf "${STORE:?}/ramses_L5_chi${chi}"
      nice -n 19 $PY /home/kaan/dense_export.py "ramses_L5_chi${chi}" ramses "$chi" "$STORE" $(ls -d $d/output_* | sort) >> "$LOG" 2>&1
      nice -n 19 $PY /home/kaan/diagnostics.py "ramses_L5_chi${chi}" ramses "$chi" "$($PY -c "import math;print(math.sqrt($chi)/2.582)")" $(ls -d $d/output_* | sort) >> "$LOG" 2>&1
      say "  ramses_L5_chi${chi}: $n raw into $(ls $STORE/ramses_L5_chi${chi}/f*.bin 2>/dev/null | wc -l) frames"
    fi
  fi
  d=$CO/enzo/runs/CW3D_L4_chi${chi}
  if [ -d "$d" ]; then
    fs=$(ls -d $d/DD*/CW_[0-9][0-9][0-9][0-9] 2>/dev/null | sort)
    if [ -n "$fs" ]; then
      rm -rf "${STORE:?}/enzo_L4_chi${chi}"
      nice -n 19 $PY /home/kaan/dense_export.py "enzo_L4_chi${chi}" enzo "$chi" "$STORE" $fs >> "$LOG" 2>&1
      say "  enzo_L4_chi${chi}: into $(ls $STORE/enzo_L4_chi${chi}/f*.bin 2>/dev/null | wc -l) frames"
    fi
  fi
done
[ -x "$SWEEP" ] && bash "$SWEEP" >/dev/null 2>&1
say "  free after sweep: $(freegb)GB"
publish

# ------------------------------------------------------ B and D: AthenaPK GPU
apk_run() {
  local L=$1 chi=$2 M=$3 cool=${4:-}
  local nx ny mb v tlim dt tcc tag d rc n t0
  nx=$(( 8 * (2 ** L) )); ny=$(( nx / 2 )); mb=16
  v=$($PY -c "print($M*$CS)")
  tcc=$($PY -c "import math;print(math.sqrt($chi)/($M*$CS))")
  tlim=$($PY -c "import math;print(5*math.sqrt($chi)/($M*$CS))")
  dt=$($PY -c "import math;print(5*math.sqrt($chi)/($M*$CS)/20)")
  if [ -n "$cool" ]; then
    tag="apkcool_L${L}_chi${chi}"
  else
    tag="apkM$(echo $M | tr -d .)_L${L}_chi${chi}"
  fi
  if [ "$(ls $STORE/$tag/f*.bin 2>/dev/null | wc -l)" -ge 18 ]; then say "  HAVE $tag"; return; fi
  if ! need_disk 30; then say "  SKIP $tag (disk $(freegb)GB)"; return; fi
  d=$CO/athenapk/runs/WK_${tag}
  mkdir -p "$d" || return
  if ! $PY /home/kaan/mkinput.py "$CO/athenapk/runs/M3D_L5_chi10/athinput" "$d/athinput" "$ny" "$nx" "$ny" "$mb" "$tlim" "$dt" "$chi" "$v" $cool >> "$LOG" 2>&1; then
    say "  SKIP $tag (input generation failed)"; return
  fi
  cd "$d" || return
  rm -f ./*.phdf
  t0=$(date +%s)
  timeout 21600 "$APK" -i athinput > run.out 2>&1
  rc=$?
  n=$(ls ./*.phdf 2>/dev/null | wc -l)
  say "  $tag rc=$rc snaps=$n wall=$(( $(date +%s)-t0 ))s"
  if [ "$n" -ge 5 ]; then harvest "$tag" apk "$chi" "$tcc" "$d" '*.phdf'; fi
}

say ""
say "--- B: Mach 0.5 / 1.5 / 5 on AthenaPK (GPU) ---"
for M in 5 1.5 0.5; do
  for chi in 10 100 1000; do apk_run 4 "$chi" "$M"; done
done
publish
for M in 5 1.5 0.5; do
  for chi in 10 100 1000; do apk_run 5 "$chi" "$M"; done
done
publish

say ""
say "--- D: radiative cooling, Townsend 2009 exact integration ---"
if [ -f "$COOLTBL" ]; then
  for chi in 10 100 1000; do apk_run 4 "$chi" 2.0 "$COOLTBL"; done
  for chi in 10 100; do apk_run 5 "$chi" 2.0 "$COOLTBL"; done
else
  say "  cooling table missing at $COOLTBL, skipped"
fi
publish

# --------------------------------------------------- C: Mach on the CPU codes
cpu_mach() {
  local code=$1 chi=$2 M=$3
  local v tlim dt tcc tag d rc n t0
  v=$($PY -c "print($M*$CS)")
  tcc=$($PY -c "import math;print(math.sqrt($chi)/($M*$CS))")
  tlim=$($PY -c "import math;print(5*math.sqrt($chi)/($M*$CS))")
  dt=$($PY -c "import math;print(5*math.sqrt($chi)/($M*$CS)/20)")
  tag="${code}M$(echo $M | tr -d .)_L4_chi${chi}"
  if [ "$(ls $STORE/$tag/f*.bin 2>/dev/null | wc -l)" -ge 18 ]; then say "  HAVE $tag"; return; fi
  if ! need_disk 40; then say "  SKIP $tag (disk $(freegb)GB)"; return; fi
  while [ "$(availram)" -lt 8 ]; do sleep 60; done
  t0=$(date +%s)
  case $code in
    athpp)
      d=$CO/athenapp/runs/WK_${tag}; mkdir -p "$d"; cd "$d" || return
      sed -e "s/^Mach *=.*/Mach = $M/" -e "s/^drat *=.*/drat = ${chi}.0/" \
          -e "s/^tlim *=.*/tlim = $tlim/" -e "s/^dt *=.*/dt = $dt/" \
          -e "s/^nx1 *= *256/nx1 = 128/" -e "s/^nx2 *= *128/nx2 = 64/" -e "s/^nx3 *= *128/nx3 = 64/" \
          "$CO/athenapp/runs/M3D_ATHPP_L5_chi10/athinput.cloud_wind" > athinput.cloud_wind
      rm -f ./*.athdf
      timeout 43200 nice -n 5 mpirun --oversubscribe -np 8 "$CO/athenapp/bin/athena" -i athinput.cloud_wind -d . > run.out 2>&1
      rc=$?; n=$(ls ./*.athdf 2>/dev/null | wc -l)
      say "  $tag rc=$rc snaps=$n wall=$(( $(date +%s)-t0 ))s"
      if [ "$n" -ge 5 ]; then harvest "$tag" athpp "$chi" "$tcc" "$d" '*.athdf'; fi
      ;;
    athw)
      d=$A8/WK_${tag}; mkdir -p "$d"; cd "$d" || return
      sed -e "s/^Mach *=.*/Mach = $M/" -e "s/^drat *=.*/drat = $chi/" \
          -e "s/^tlim *=.*/tlim = $tlim/" -e "s/^dt *=.*/dt = $dt/" \
          -e "s/^Nx1 *=.*/Nx1 = 128/" -e "s/^Nx2 *=.*/Nx2 = 64/" -e "s/^Nx3 *=.*/Nx3 = 64/" \
          -e "s/^NGrid_x1 *=.*/NGrid_x1 = 2/" -e "s/^NGrid_x2 *=.*/NGrid_x2 = 2/" -e "s/^NGrid_x3 *=.*/NGrid_x3 = 2/" \
          "$A8/M3D_ATHW_L5_chi10/athinput" > athinput
      cp -f "$A8/M3D_ATHW_L5_chi10/athena_redo3d" ./athena_wk 2>/dev/null
      rm -rf id*
      timeout 43200 nice -n 5 mpirun --oversubscribe -np 8 ./athena_wk -i athinput > run.out 2>&1
      rc=$?; n=$(ls id0/*.vtk 2>/dev/null | wc -l)
      say "  $tag rc=$rc snaps=$n wall=$(( $(date +%s)-t0 ))s"
      if [ "$n" -ge 5 ]; then harvest "$tag" athw "$chi" "$tcc" "$d/id0" '*.vtk'; fi
      ;;
    enzo)
      d=$CO/enzo/runs/WK_${tag}; mkdir -p "$d"; cd "$d" || return
      sed -e "s/^CloudWindVelocity.*/CloudWindVelocity          = $v/" \
          -e "s/^CloudWindChi.*/CloudWindChi               = ${chi}.0/" \
          -e "s/^StopTime.*/StopTime                   = $tlim/" \
          -e "s/^dtDataDump.*/dtDataDump                 = $dt/" \
          -e "s/^TopGridDimensions.*/TopGridDimensions = 128 64 64/" \
          "$CO/enzo/runs/CW3D_L4_chi10/CloudWind.enzo" > CloudWind.enzo
      cp -f "$CO/enzo/runs/CW3D_chi10_256/enzo.exe" ./enzo.exe 2>/dev/null
      rm -rf DD0*
      timeout 43200 nice -n 5 mpirun --oversubscribe -np 8 ./enzo.exe -d CloudWind.enzo > run.out 2>&1
      rc=$?; n=$(ls -d DD0* 2>/dev/null | wc -l)
      say "  $tag rc=$rc snaps=$n wall=$(( $(date +%s)-t0 ))s"
      if [ "$n" -ge 5 ]; then harvest "$tag" enzo "$chi" "$tcc" "$d" 'DD*/CW_[0-9][0-9][0-9][0-9]'; fi
      ;;
  esac
}

say ""
say "--- C: Mach 0.5 / 1.5 / 5 on Athena++, Athena 4.2, Enzo (level 4) ---"
for M in 5 1.5 0.5; do
  for chi in 10 100 1000; do
    for code in athpp athw enzo; do cpu_mach "$code" "$chi" "$M"; done
  done
  publish
done

# ------------------------------------------- E: level 5 Lagrangian, serial
lag5() {
  local label=$1 d=$2 tag=$3 kind=$4 chi=$5
  local n tcc t0
  if [ ! -d "$d" ] || [ ! -x "$d/run.sh" ]; then say "  SKIP $label"; return; fi
  if [ "$(ls $STORE/$tag/f*.bin 2>/dev/null | wc -l)" -ge 90 ]; then say "  HAVE $label"; return; fi
  if ! need_disk 60; then say "  SKIP $label (disk $(freegb)GB)"; return; fi
  while [ "$(availram)" -lt 12 ]; do sleep 120; done
  rm -rf "$d/output"; mkdir -p "$d/output"
  cd "$d" || return
  t0=$(date +%s)
  timeout 86400 nice -n 5 ./run.sh > launch.out 2>&1
  n=$(ls "$d"/output/snap*.hdf5 "$d"/output/snapshot*.hdf5 "$d"/*.0000?? 2>/dev/null | wc -l)
  say "  $label snaps=$n wall=$(( $(date +%s)-t0 ))s free=$(freegb)GB"
  tcc=$($PY -c "import math;print(math.sqrt($chi)/2.582)")
  export P3D_CEN="3,5,5" P3D_DIMS="128,64,64"
  if [ "$n" -ge 5 ]; then
    if [ "$kind" = "tipsy" ]; then
      harvest "$tag" tipsy "$chi" "$tcc" "$d" '*.0000??'
    else
      harvest "$tag" part "$chi" "$tcc" "$d/output" 'snap*.hdf5'
    fi
  fi
}

say ""
say "--- E: level 5 Lagrangian (serial, 8 ranks each) ---"
for chi in 10 100 1000; do
  lag5 "GIZMO-MFM L5 chi=$chi" "$CO/gizmo/runs/GZ_L5_chi${chi}_mfm" "gzmfm_L5_chi${chi}" part "$chi"
  lag5 "GIZMO-MFV L5 chi=$chi" "$CO/gizmo/runs/GZ_L5_chi${chi}_mfv" "gzmfv_L5_chi${chi}" part "$chi"
  lag5 "Gasoline  L5 chi=$chi" "$CO/gasoline/runs/CW3D_L5_chi${chi}" "gas_L5_chi${chi}" tipsy "$chi"
  lag5 "Arepo     L5 chi=$chi" "$CO/arepo/runs/AREPO3D_L5_chi${chi}" "arepo_L5_chi${chi}" part "$chi"
  publish
done

# ---------------------------------------------------------- F: figures
say ""
say "--- F: regenerate figures and publish ---"
nice -n 19 $PY /home/kaan/fig1b.py "$FIG/figure1_3d_L3_t3.png" L3 apk,athpp,athw,enzo,ramses,arepo,gzmfm,gas 3.0 >> "$LOG" 2>&1
nice -n 19 $PY /home/kaan/fig1b.py "$FIG/figure1_3d_L3_t5.png" L3 apk,athpp,athw,enzo,ramses,arepo,gzmfm,gas 5.0 >> "$LOG" 2>&1
nice -n 19 $PY /home/kaan/fig1b.py "$FIG/figure1_3d_L4_t5.png" L4 apk,athpp,athw,enzo,ramses,arepo,gzmfm,gzmfv,gas 5.0 >> "$LOG" 2>&1
nice -n 19 $PY /home/kaan/fig1b.py "$FIG/figure1_3d_L5_t5.png" L5 apk,enzo,flashx,ramses,gzmfm,gzmfv 5.0 >> "$LOG" 2>&1
nice -n 19 $PY /home/kaan/fig1b.py "$FIG/figure1_mach_L4.png" L4 apkM05,apkM15,apk,apkM5 5.0 >> "$LOG" 2>&1
nice -n 19 $PY /home/kaan/fig1b.py "$FIG/figure1_mach_L5.png" L5 apkM05,apkM15,apk,apkM5 5.0 >> "$LOG" 2>&1
nice -n 19 $PY /home/kaan/fig1b.py "$FIG/figure1_cooling_L4.png" L4 apk,apkcool 5.0 >> "$LOG" 2>&1
for L in L3 L4 L5; do
  nice -n 19 $PY /home/kaan/fig2.py "$FIG/figure2_mass_$L.png" "$L" >> "$LOG" 2>&1
done
publish
say ""
say "=== WEEK QUEUE DONE $(date) ==="
say "dense runs: $(ls -d $STORE/*/ 2>/dev/null | grep -c chi)   free: $(freegb)GB"
