#!/usr/bin/env bash
set -euo pipefail
cd /home/user/performance_20260907c
exec 9>/home/user/performance_20260907/production.lock
flock -n 9
test ! -e profiles_before_l5_io.json
cp /home/user/performance_20260907/optimized_profiles.json profiles_before_l5_io.json
cp /mnt/c/Users/user/CloudCrushing/performance_20260907/optimized_profiles.json /home/user/performance_20260907/optimized_profiles.json
/home/user/venv/bin/python /home/user/performance_20260907/test_optimized.py
