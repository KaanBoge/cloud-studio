#!/usr/bin/env bash
set -euo pipefail
src=/mnt/c/Users/user/CloudCrushing
work=/home/user/followup_20260907
mkdir -p "$work/before" "$work/evidence"
for entry in /home/user/verified_20260907/run_corrected_athpp.py /home/user/performance_20260907/run_optimized.py; do
  dest="$work/before/$(basename "$entry")"
  if [ -e "$entry" ] && [ ! -e "$dest" ]; then cp -p "$entry" "$dest"; fi
done
cp "$src/audit_20260907/storage_guard.py" /home/user/verified_20260907/storage_guard.py
cp "$src/audit_20260907/run_corrected_athpp.py" /home/user/verified_20260907/run_corrected_athpp.py
cp "$src/performance_20260907/run_optimized.py" /home/user/performance_20260907/run_optimized.py
cp "$src/performance_20260907/test_optimized.py" /home/user/performance_20260907/test_optimized.py
cp "$src/performance_20260907/optimized_profiles.json" /home/user/performance_20260907/optimized_profiles.json
cp "$src/followup_20260907/test_storage_guard.py" "$work/"
cp "$src/followup_20260907/test_comparison_checks.py" "$work/"
for file in cooling_audit.py test_cooling_guard.py mkinput_legacy.py; do cp "$src/followup_20260907/$file" "$work/$file"; done
if [ ! -e "$work/before/mkinput.py" ]; then cp -p /home/user/mkinput.py "$work/before/mkinput.py"; fi
cp "$src/followup_20260907/mkinput_legacy.py" /home/user/mkinput.py
for file in comparison_checks.py figure1_v2.py figure2_v2.py diagnostics_v2.py; do
  if [ -f "/home/user/verified_20260907/$file" ] && [ ! -e "$work/before/$file" ]; then
    cp -p "/home/user/verified_20260907/$file" "$work/before/$file"
  fi
  cp "$src/audit_20260907/$file" "/home/user/verified_20260907/$file"
done
for file in week_queue.sh gal_queue.sh; do
  if [ ! -e "$work/before/$file" ]; then cp -p "/home/user/$file" "$work/before/$file"; fi
  cp "$src/followup_20260907/retired_queue.sh" "/home/user/$file"
done
export PYTHONPATH=/home/user/verified_20260907:/home/user/performance_20260907
/home/user/venv/bin/python -m unittest discover -s "$work" -p test_storage_guard.py -v
/home/user/venv/bin/python -m unittest discover -s "$work" -p test_comparison_checks.py -v
/home/user/venv/bin/python -m unittest discover -s "$work" -p test_cooling_guard.py -v
/home/user/venv/bin/python "$work/cooling_audit.py" --root /home/user/codes/athenapk/runs --out "$work/evidence/cooling_audit.json"
/home/user/venv/bin/python /home/user/verified_20260907/storage_guard.py /home/user --required-gib 2
cd /home/user/performance_20260907
/home/user/venv/bin/python -m unittest test_optimized.py -v
