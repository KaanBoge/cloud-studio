$ErrorActionPreference='Stop'
$taskStudy='C:\Users\kaanb\CloudCrushing\sensitivity_20260907'
$taskSource=Join-Path $taskStudy 'flash'
$taskDestination='C:\Users\kaanb\cloud-studio-repo\analysis\sensitivity_20260907\flash'
$taskProof=Get-Content -LiteralPath (Join-Path $taskSource 'smoke_batch.json') -Raw | ConvertFrom-Json
$taskYT=Get-Content -LiteralPath (Join-Path $taskSource 'yt_smoke_validation.json') -Raw | ConvertFrom-Json
if($taskProof.status -ne 'complete_native_checks' -or $taskYT.status -ne 'passed'){throw 'Validated native setup required'}
if(Test-Path -LiteralPath $taskDestination){throw 'Publication directory exists; inspect before updating'}
New-Item -ItemType Directory -Path $taskDestination | Out-Null
$taskFiles=@('README.md','build_flash.py','run_flash.py','test_flash.py','verify_setup.py','inspect_native.py','inspect_pair.py','analyze_flash.py','test_analysis_flash.py','verify_yt_smokes.py','export_inputs.py','launch_windows.ps1','build.json','smoke_batch.json','smoke_pair_strict_check.json','setup_validation.json','yt_smoke_validation.json','planned_inputs.json')
foreach($taskFile in $taskFiles){
  $taskFrom=Join-Path $taskSource $taskFile;$taskTo=Join-Path $taskDestination $taskFile
  Copy-Item -LiteralPath $taskFrom -Destination $taskTo
  if((Get-FileHash -LiteralPath $taskFrom).Hash -ne (Get-FileHash -LiteralPath $taskTo).Hash){throw 'Copy hash mismatch'}
}
foreach($taskFolder in @('source','planned_inputs')){Copy-Item -LiteralPath (Join-Path $taskSource $taskFolder) -Destination (Join-Path $taskDestination $taskFolder) -Recurse}
foreach($taskFile in @('README.md','PLAN.md')){
  $taskTarget=Join-Path (Split-Path $taskDestination) $taskFile;$taskTemporary=$taskTarget+'.publish.tmp'
  if(Test-Path -LiteralPath $taskTemporary){throw 'Unexpected temporary publication file'}
  Copy-Item -LiteralPath (Join-Path $taskStudy $taskFile) -Destination $taskTemporary
  Move-Item -LiteralPath $taskTemporary -Destination $taskTarget -Force
}
$taskBytes=(Get-ChildItem -LiteralPath $taskDestination -File -Recurse|Measure-Object Length -Sum).Sum
if($taskBytes -gt 10MB){throw 'Unexpectedly large setup package'}
[pscustomobject]@{path=$taskDestination;bytes=$taskBytes;scope='Setup and validation evidence; full-run analysis pending'}|ConvertTo-Json
