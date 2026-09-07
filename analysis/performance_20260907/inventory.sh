#!/bin/bash
set -eu
echo 'RESOURCES'
free -h
df -h /home/kaan
lscpu -e=CPU,CORE,SOCKET,ONLINE
nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total --format=csv,noheader
echo 'ACTIVE'
ps -eo pid,pcpu,rss,comm,args --sort=-pcpu | head -16
echo 'NATIVE RUN DIRECTORIES'
for base in /home/kaan/codes/athenapp/runs /home/kaan/codes/athenapk/runs /home/kaan/codes/enzo/runs /home/kaan/CloudCrushing/A8 /home/kaan/codes/flashx/runs /home/kaan/codes/ramses/runs; do
  echo "$base"
  find "$base" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort
done
echo 'BUILD CONFIGURATION'
head -90 /home/kaan/codes/athenapp/Makefile
grep -E 'CMAKE_BUILD_TYPE|CMAKE_CXX_FLAGS|Kokkos_ARCH|CMAKE_CUDA_FLAGS' /home/kaan/codes/athenapk/build-cuda/CMakeCache.txt
