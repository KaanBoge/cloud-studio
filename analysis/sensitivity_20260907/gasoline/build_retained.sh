#!/usr/bin/env bash
set -euo pipefail
root=/home/kaan/sensitivity_20260907/gasoline
test ! -e "$root/build_retained.log"
exec 9>/home/kaan/performance_20260907/benchmark.lock
flock -n 9
exec 8>/home/kaan/performance_20260907/production.lock
flock -n 8
test "$(df -B1 --output=avail "$root" | tail -n 1)" -gt 11811160064
test "$(df -B1 --output=avail /mnt/c | tail -n 1)" -gt 11811160064
cd "$root/native_retained/gasoline"
set -o noclobber
timeout 600 nice -n 19 make -j2 mpi > "$root/build_retained.log" 2>&1
test ! -e "$root/checkpoint_probe"
gcc -O2 -I. "$root/checkpoint_probe.c" fdl.o htable.o -lm -o "$root/checkpoint_probe"
sha256sum gasoline "$root/checkpoint_probe"
