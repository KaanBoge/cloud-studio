#!/usr/bin/env bash
set -euo pipefail
work=/home/user/followup_20260907
src=/mnt/c/Users/user/CloudCrushing/followup_20260907
mkdir -p "$work/bin" "$work/logs"
exec 9>"$work/build.lock"
flock -n 9
/home/user/venv/bin/python /home/user/verified_20260907/storage_guard.py "$work" --required-gib 1
cp "$src/cloud_wind_tracking.cpp" /home/user/codes/athenapp/src/pgen/cloud_wind_tracking.cpp
nice -n 19 make -C /home/user/codes/athenapp -j2 PROBLEM_FILE=cloud_wind_tracking.cpp \
  OBJ_DIR=obj_tracking20260907/ EXE_DIR="$work/bin/" EXECUTABLE="$work/bin/athpp_tracking" \
  >> "$work/logs/build_tracking.log" 2>&1
sha256sum "$work/bin/athpp_tracking" /home/user/codes/athenapp/src/pgen/cloud_wind_tracking.cpp
