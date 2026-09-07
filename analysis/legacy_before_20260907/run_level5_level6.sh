#!/bin/bash
# ============================================================================
# LEVEL 5 AND LEVEL 6 RUNS, all codes.
#
# Added after review: run_ladder.sh only covers levels 1 to 4, so the shared
# scripts made it look as though nothing above level 4 had been run. These are
# the commands that actually produced the level 5 and level 6 data.
#
#   level 5 = 256 x 128 x 128   12.8 cells per cloud radius
#   level 6 = 512 x 256 x 256   25.6 cells per cloud radius
#             (the Braspenning et al. 2023 reference resolution)
#
# Level 7 (1024 x 512 x 256) is not reachable on this machine: 90 to 160 GB of
# memory against 32 GB installed.
#
# Usage:  run_level5_level6.sh <level> <chi> [code ...]
#   e.g.  run_level5_level6.sh 6 10 apk athpp
#         run_level5_level6.sh 5 100          (all codes)
# ============================================================================
set -u
L=${1:?level, 5 or 6}
CHI=${2:?chi, 10 100 or 1000}
shift 2
CODES=${*:-apk athpp athw enzo flashx flash ramses}

PY=/home/kaan/venv/bin/python
CO=/home/kaan/codes
A8=/home/kaan/CloudCrushing/A8
STORE=/mnt/c/Users/kaanb/cloud-frames-repo
LOG=/mnt/c/Users/kaanb/CloudCrushing/results_A8/level${L}.log

NX=$(( 8 * (2 ** L) ))          # streamwise cells
NY=$(( NX / 2 ))                # transverse
VW=2.581989                     # Mach 2 in units where c_s = sqrt(5/3)
TLIM=$($PY -c "import math;print('%.6f'%(5*math.sqrt($CHI)/$VW))")
DT=$($PY -c "import math;print('%.6f'%(5*math.sqrt($CHI)/$VW/100))")
TCC=$($PY -c "import math;print('%.6f'%(math.sqrt($CHI)/$VW))")

echo "=== LEVEL $L, chi=$CHI, ${NY}x${NX}x${NY}, tmax=$TLIM, dt=$DT ===" | tee -a "$LOG"

# Memory guard. Level 6 needs roughly 12 GB for the grid codes; refuse rather
# than let the OOM killer take a run eight hours in.
need_ram() {
  local want=$1 have
  have=$(free -g | awk '/Mem:/{print $7}')
  if [ "${have:-0}" -lt "$want" ]; then
    echo "  SKIP: ${have} GB free, need ${want} GB" | tee -a "$LOG"; return 1
  fi
}

harvest() { # tag kind dir glob
  local files; files=$(ls -d $3/$4 2>/dev/null | sort)
  [ -z "$files" ] && return
  $PY /home/kaan/dense_export.py "$1" "$2" "$CHI" "$STORE" $files >> "$LOG" 2>&1
  $PY /home/kaan/diagnostics.py  "$1" "$2" "$CHI" "$TCC" $files >> "$LOG" 2>&1
  echo "  $1: $(ls $STORE/$1/f*.bin 2>/dev/null | wc -l) frames" | tee -a "$LOG"
}

for code in $CODES; do
  case $code in

    # ---- AthenaPK, single GPU. Input written by make_athenapk_input.py so the
    #      mesh block cannot be clobbered by the meshblock block.
    apk)
      need_ram 4 || continue
      d=$CO/athenapk/runs/M3D_L${L}_chi${CHI}; mkdir -p "$d"
      $PY /home/kaan/make_athenapk_input.py \
          "$CO/athenapk/runs/M3D_L5_chi10/athinput" "$d/athinput" \
          "$NY" "$NX" "$NY" 16 "$TLIM" "$DT" "$CHI" "$VW" || continue
      ( cd "$d" && rm -f ./*.phdf && \
        "$CO/athenapk/build-cuda/bin/athenaPK" -i athinput > run.out 2>&1 )
      harvest "apk_L${L}_chi${CHI}" apk "$d" '*.phdf' ;;

    # ---- Athena++, 8 MPI ranks
    athpp)
      need_ram 10 || continue
      d=$CO/athenapp/runs/M3D_ATHPP_L${L}_chi${CHI}; mkdir -p "$d"
      sed -e "s/^drat *=.*/drat = ${CHI}.0/" -e "s/^tlim *=.*/tlim = $TLIM/" \
          -e "s/^dt *=.*/dt = $DT/" \
          -e "s/^nx1 *= *256/nx1 = $NX/" -e "s/^nx2 *= *128/nx2 = $NY/" \
          -e "s/^nx3 *= *128/nx3 = $NY/" \
          "$CO/athenapp/runs/M3D_ATHPP_L5_chi10/athinput.cloud_wind" > "$d/athinput.cloud_wind"
      ( cd "$d" && rm -f ./*.athdf && \
        mpirun --bind-to core -np 8 "$CO/athenapp/bin/athena" \
               -i athinput.cloud_wind -d . > run.out 2>&1 )
      harvest "athpp_L${L}_chi${CHI}" athpp "$d" '*.athdf' ;;

    # ---- Athena 4.2, 8 ranks, NGrid must multiply to the rank count
    athw)
      need_ram 10 || continue
      d=$A8/M3D_ATHW_L${L}_chi${CHI}; mkdir -p "$d"
      sed -e "s/^drat *=.*/drat = $CHI/" -e "s/^tlim *=.*/tlim = $TLIM/" \
          -e "s/^dt *=.*/dt = $DT/" \
          -e "s/^Nx1 *=.*/Nx1 = $NX/" -e "s/^Nx2 *=.*/Nx2 = $NY/" -e "s/^Nx3 *=.*/Nx3 = $NY/" \
          -e "s/^NGrid_x1 *=.*/NGrid_x1 = 2/" -e "s/^NGrid_x2 *=.*/NGrid_x2 = 2/" \
          -e "s/^NGrid_x3 *=.*/NGrid_x3 = 2/" \
          "$A8/M3D_ATHW_L5_chi10/athinput" > "$d/athinput"
      cp -f "$A8/M3D_ATHW_L5_chi10/athena_redo3d" "$d/athena_run" 2>/dev/null
      ( cd "$d" && rm -rf id* && \
        mpirun --bind-to core -np 8 ./athena_run -i athinput > run.out 2>&1 )
      harvest "athw_L${L}_chi${CHI}" athw "$d/id0" '*.vtk' ;;

    # ---- Enzo, unigrid
    enzo)
      need_ram 12 || continue
      d=$CO/enzo/runs/CW3D_L${L}_chi${CHI}; mkdir -p "$d"
      sed -e "s/^TopGridDimensions.*/TopGridDimensions = $NX $NY $NY/" \
          -e "s/^CloudWindChi.*/CloudWindChi               = ${CHI}.0/" \
          -e "s/^StopTime.*/StopTime                   = $TLIM/" \
          -e "s/^dtDataDump.*/dtDataDump                 = $DT/" \
          "$CO/enzo/runs/CW3D_L4_chi10/CloudWind.enzo" > "$d/CloudWind.enzo"
      cp -f "$CO/enzo/runs/CW3D_chi10_256/enzo.exe" "$d/enzo.exe" 2>/dev/null
      ( cd "$d" && rm -rf DD0* && \
        mpirun --bind-to core -np 8 ./enzo.exe -d CloudWind.enzo > run.out 2>&1 )
      harvest "enzo_L${L}_chi${CHI}" enzo "$d" 'DD*/CW_[0-9][0-9][0-9][0-9]' ;;

    # ---- Flash-X. Level 6 needs its own object directory, built with
    #      ./setup CloudWind -auto -3d +pm4dev -nxb=16 -nyb=16 -nzb=16 \
    #               -maxblocks=600 -objdir=object_3d_l6
    flashx)
      need_ram 12 || continue
      obj=object_3d; [ "$L" -ge 6 ] && obj=object_3d_l6
      d=$CO/flashx/runs/prod3d_l${L}_chi${CHI}; mkdir -p "$d"
      sed -e "s/^sim_rhoCloud.*/sim_rhoCloud    = ${CHI}.0/" \
          -e "s/^tmax.*/tmax = $TLIM/" \
          -e "s/^plotfileIntervalTime.*/plotfileIntervalTime = $DT/" \
          "$CO/flashx/runs/prod3d_chi10/flash.par" > "$d/flash.par"
      cp -f "$CO/flashx/$obj/flashx" "$d/flashx" 2>/dev/null
      ( cd "$d" && mpirun --oversubscribe -np 8 ./flashx > run.out 2>&1 )
      harvest "flashx_L${L}_chi${CHI}" flashx "$d" '*hdf5_plt_cnt_????' ;;

    # ---- FLASH 4.8. NOTE R_cloud = 0.1 here, not 1.0, so its t_cc is ten times
    #      smaller than every other code's. Pass the right one to diagnostics.
    flash)
      need_ram 12 || continue
      d=$A8/M3D_FLASH48_L${L}_chi${CHI}; mkdir -p "$d"
      TCCF=$($PY -c "import math;print('%.6f'%(math.sqrt($CHI)*0.1/$VW))")
      TLF=$($PY -c "import math;print('%.6f'%(5*math.sqrt($CHI)*0.1/$VW))")
      sed -e "s/^sim_rhoCloud.*/sim_rhoCloud = ${CHI}.0/" \
          -e "s/^tmax.*/tmax = $TLF/" \
          "$A8/M3D_FLASH48_L5_chi10/flash.par" > "$d/flash.par"
      ( cd "$d" && mpirun --oversubscribe -np 12 ./flash4 > run.out 2>&1 )
      files=$(ls "$d"/cloudcrush_hdf5_plt_cnt_* 2>/dev/null | sort)
      [ -n "$files" ] && $PY /home/kaan/dense_export.py "flash_L${L}_chi${CHI}" flash "$CHI" "$STORE" $files >> "$LOG" 2>&1
      [ -n "$files" ] && $PY /home/kaan/diagnostics.py "flash_L${L}_chi${CHI}" flash "$CHI" "$TCCF" $files >> "$LOG" 2>&1 ;;

    # ---- RAMSES. Cubic box, levelmin = levelmax = log2(streamwise cells).
    ramses)
      need_ram 10 || continue
      LV=$($PY -c "import math;print(int(math.log2($NX)))")
      d=$CO/ramses/runs/RAM3D_L${L}_chi${CHI}; mkdir -p "$d"
      sed -e "s/^ *levelmin *=.*/levelmin=$LV/" -e "s/^ *levelmax *=.*/levelmax=$LV/" \
          -e "s/^ *tend *=.*/tend=$TLIM/" \
          "$CO/ramses/runs/RAM3D_chi${CHI}/RAM3D_chi${CHI}.nml" > "$d/run.nml"
      cp -f "$CO/ramses/runs/RAM3D_chi${CHI}/ramses_cw3d" "$d/" 2>/dev/null
      ( cd "$d" && mpirun --bind-to core -np 8 ./ramses_cw3d run.nml > run.out 2>&1 )
      harvest "ramses_L${L}_chi${CHI}" ramses "$d" 'output_[0-9]*' ;;
  esac
done

echo "=== done $(date) ===" | tee -a "$LOG"
