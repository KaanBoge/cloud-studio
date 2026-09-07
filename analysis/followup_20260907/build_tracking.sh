#!/usr/bin/env bash
set -euo pipefail
work=/home/kaan/followup_20260907
src=/mnt/c/Users/kaanb/CloudCrushing/followup_20260907
mkdir -p "$work/bin" "$work/logs"
exec 9>"$work/build.lock"
flock -n 9
/home/kaan/venv/bin/python /home/kaan/verified_20260907/storage_guard.py "$work" --required-gib 1
cp "$src/cloud_wind_tracking.cpp" /home/kaan/codes/athenapp/src/pgen/cloud_wind_tracking.cpp
nice -n 19 make -C /home/kaan/codes/athenapp -j2 PROBLEM_FILE=cloud_wind_tracking.cpp \
  OBJ_DIR=obj_tracking20260907/ EXE_DIR="$work/bin/" EXECUTABLE="$work/bin/athpp_tracking" \
  >> "$work/logs/build_tracking.log" 2>&1
sha256sum "$work/bin/athpp_tracking" /home/kaan/codes/athenapp/src/pgen/cloud_wind_tracking.cpp
