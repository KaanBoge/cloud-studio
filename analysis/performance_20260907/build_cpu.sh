#!/bin/bash
set -eu
ROOT=/home/kaan/performance_20260907
mkdir -p "$ROOT/bin" "$ROOT/logs"
cd /home/kaan/codes/athenapp
nice -n 19 make -j2 OBJ_DIR=obj_perf20260907/ EXE_DIR="$ROOT/bin/" \
  EXECUTABLE="$ROOT/bin/athpp_native" \
  CXXFLAGS='-O3 -march=native -fno-fast-math -ffp-contract=off -std=c++11 -I/usr/include/hdf5/openmpi' \
  > "$ROOT/logs/build_native.log" 2>&1
sha256sum "$ROOT/bin/athpp_native"
