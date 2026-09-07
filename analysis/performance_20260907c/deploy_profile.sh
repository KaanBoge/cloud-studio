#!/usr/bin/env bash
set -euo pipefail
cd /home/kaan/performance_20260907c
exec 9>/home/kaan/performance_20260907/production.lock
flock -n 9
test ! -e profiles_before_l5_io.json
cp /home/kaan/performance_20260907/optimized_profiles.json profiles_before_l5_io.json
cp /mnt/c/Users/kaanb/CloudCrushing/performance_20260907/optimized_profiles.json /home/kaan/performance_20260907/optimized_profiles.json
/home/kaan/venv/bin/python /home/kaan/performance_20260907/test_optimized.py
