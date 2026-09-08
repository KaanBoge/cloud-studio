#!/usr/bin/env bash
set -euo pipefail
root=/home/kaan/sensitivity_20260907/gasoline
test ! -e "$root/build.log"
exec 9>/home/kaan/performance_20260907/benchmark.lock
flock -n 9
exec 8>/home/kaan/performance_20260907/production.lock
flock -n 8
guest_free=$(df -B1 --output=avail "$root" | tail -n 1)
host_free=$(df -B1 --output=avail /mnt/c | tail -n 1)
mem_kb=$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)
test "$guest_free" -gt 11811160064
test "$host_free" -gt 11811160064
test "$mem_kb" -gt 4194304
cd "$root/native/gasoline"
set -o noclobber
timeout 600 nice -n 19 make -j2 mpi > "$root/build.log" 2>&1
sha256sum gasoline "$root/gasoline_original"
