#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' 'RETAINED COOLING INPUTS'
find /home/kaan/codes/athenapk/runs -maxdepth 2 -type f -path '*cool*/athinput' -print -exec grep -n -E 'enable_cooling|integrator|T_wind_cgs|code_.*_cgs|table_filename|cooling' {} \;
printf '%s\n' 'NATIVE COOLING CONSTRUCTOR'
sed -n '730,750p' /home/kaan/codes/athenapk/src/hydro/hydro.cpp
grep -n -E 'Get.*String|integrator|townsend|exact|table_filename|lambda_units' /home/kaan/codes/athenapk/src/hydro/srcterms/tabular_cooling.cpp | head -40
