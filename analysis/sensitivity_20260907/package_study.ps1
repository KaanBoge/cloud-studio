$ErrorActionPreference = 'Stop'
$taskSource = 'C:\Users\kaanb\CloudCrushing\sensitivity_20260907'
$taskDest = 'C:\Users\kaanb\cloud-studio-repo\analysis\sensitivity_20260907'
if (Test-Path -LiteralPath $taskDest) { throw 'Package exists; inspect before updating' }
New-Item -ItemType Directory -Path $taskDest | Out-Null
$taskFiles = @('README.md','PLAN.md','build.py','run_pairs.py','test_pairs.py','analyze.py','test_analysis.py','crosscheck_l4.py','record_sources.py','build.json','batch.json','historical_sources.json')
foreach ($taskFile in $taskFiles) { Copy-Item -LiteralPath (Join-Path $taskSource $taskFile) -Destination (Join-Path $taskDest $taskFile) }
foreach ($taskFolder in @('source','analysis')) { Copy-Item -LiteralPath (Join-Path $taskSource $taskFolder) -Destination (Join-Path $taskDest $taskFolder) -Recurse }
New-Item -ItemType Directory -Path (Join-Path $taskDest 'athw') | Out-Null
foreach ($taskFile in @('README.md','cloud_wind.c','build_athw.py','run_athw.py','analyze_athw.py','test_athw.py','test_analysis_athw.py','launch_windows.ps1','report.json','mass_and_retention.png','build.json','batch.json','smoke_batch.json')) {
  Copy-Item -LiteralPath (Join-Path $taskSource ('athw\'+$taskFile)) -Destination (Join-Path $taskDest ('athw\'+$taskFile))
}
New-Item -ItemType Directory -Path (Join-Path $taskDest 'enzo') | Out-Null
foreach ($taskFile in @('README.md','build_enzo.py','run_enzo.py','test_enzo.py','launch_windows.ps1','run_enzo_first_attempt.py.txt','build.json','smoke_batch_v2.json')) {
  Copy-Item -LiteralPath (Join-Path $taskSource ('enzo\'+$taskFile)) -Destination (Join-Path $taskDest ('enzo\'+$taskFile))
}
Copy-Item -LiteralPath (Join-Path $taskSource 'enzo\source') -Destination (Join-Path $taskDest 'enzo\source') -Recurse
$taskBytes = (Get-ChildItem -LiteralPath $taskDest -File -Recurse | Measure-Object Length -Sum).Sum
if ($taskBytes -gt 15MB) { throw 'Unexpectedly large research package' }
Get-ChildItem -LiteralPath $taskDest -File -Recurse | ForEach-Object {
  [pscustomobject]@{path=$_.FullName.Substring($taskDest.Length+1);bytes=$_.Length;sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLower()}
} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $taskSource 'published_package_manifest.json') -Encoding utf8
[pscustomobject]@{package=$taskDest;bytes=$taskBytes} | ConvertTo-Json
