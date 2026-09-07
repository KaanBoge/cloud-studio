#!/usr/bin/env bash
set -euo pipefail
PERF_WORK=/home/kaan/performance_20260907b
mkdir -p "$PERF_WORK/bin" "$PERF_WORK/logs"
exec 9>/home/kaan/performance_20260907/benchmark.lock
flock -n 9
cd /home/kaan/codes/athenapp
nice -n 19 make -B -j2 OBJ_DIR=obj_perf20260907b_retry/ EXE_DIR="$PERF_WORK/bin/" \
 EXECUTABLE="$PERF_WORK/bin/athpp_lto" \
 CXXFLAGS='-O3 -march=native -fno-fast-math -ffp-contract=off -flto=2 -std=c++11 -I/usr/include/hdf5/openmpi' \
 > "$PERF_WORK/logs/build_lto_retry.log" 2>&1
sync
sha256sum "$PERF_WORK/bin/athpp_lto"
