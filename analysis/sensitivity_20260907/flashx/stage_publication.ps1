$ErrorActionPreference='Stop'
$taskSource='C:\Users\kaanb\CloudCrushing\sensitivity_20260907\flashx'
$taskDestination='C:\Users\kaanb\cloud-studio-repo\analysis\sensitivity_20260907\flashx'
$taskProof=Get-Content -LiteralPath (Join-Path $taskSource 'smoke_batch.json') -Raw | ConvertFrom-Json
$taskYT=Get-Content -LiteralPath (Join-Path $taskSource 'yt_smoke_validation.json') -Raw | ConvertFrom-Json
if($taskProof.status -ne 'complete_native_checks' -or $taskYT.status -ne 'passed'){throw 'Validated native setup required'}
if(Test-Path -LiteralPath $taskDestination){throw 'Publication directory exists; inspect before updating'}
New-Item -ItemType Directory -Path $taskDestination | Out-Null
$taskFiles=@('README.md','build_flashx.py','run_flashx.py','test_flashx.py','verify_setup.py','analyze_flashx.py','test_analysis_flashx.py','verify_yt_smokes.py','launch_windows.ps1','build.json','smoke_batch.json','setup_validation.json','yt_smoke_validation.json','stage_publication.ps1')
foreach($taskFile in $taskFiles){
  $taskFrom=Join-Path $taskSource $taskFile;$taskTo=Join-Path $taskDestination $taskFile
  Copy-Item -LiteralPath $taskFrom -Destination $taskTo
  if((Get-FileHash -LiteralPath $taskFrom).Hash -ne (Get-FileHash -LiteralPath $taskTo).Hash){throw 'Copy hash mismatch'}
}
Copy-Item -LiteralPath (Join-Path $taskSource 'source') -Destination (Join-Path $taskDestination 'source') -Recurse
$taskBytes=(Get-ChildItem -LiteralPath $taskDestination -File -Recurse | Measure-Object Length -Sum).Sum
if($taskBytes -gt 10MB){throw 'Unexpectedly large setup package'}
[pscustomobject]@{path=$taskDestination;bytes=$taskBytes;scope='Setup and validation evidence; full-run analysis pending'}|ConvertTo-Json
