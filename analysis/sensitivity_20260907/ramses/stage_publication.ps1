$ErrorActionPreference='Stop'
$taskStudy='C:\Users\kaanb\CloudCrushing\sensitivity_20260907'
$taskSource=Join-Path $taskStudy 'ramses'
$taskDestination='C:\Users\kaanb\cloud-studio-repo\analysis\sensitivity_20260907\ramses'
$taskReport=Get-Content -LiteralPath (Join-Path $taskSource 'report.json') -Raw | ConvertFrom-Json
if($taskReport.status -ne 'share_with_caveats' -or $taskReport.pairs.Count -ne 2){throw 'Validated completed report required'}
if(Test-Path -LiteralPath $taskDestination){throw 'Publication directory exists; review before overwriting'}
New-Item -ItemType Directory -Path $taskDestination | Out-Null
$taskFiles=@('README.md','build_ramses.py','run_ramses.py','test_ramses.py','verify_setup.py','analyze_ramses.py','test_analysis_ramses.py','launch_windows.ps1','build.json','smoke_batch.json','setup_validation.json','batch.json','report.json','mass_and_retention.png','native_reader.py','base_run.nml')
foreach($taskFile in $taskFiles){
  $taskFrom=Join-Path $taskSource $taskFile
  $taskTo=Join-Path $taskDestination $taskFile
  Copy-Item -LiteralPath $taskFrom -Destination $taskTo
  if((Get-FileHash -LiteralPath $taskFrom).Hash -ne (Get-FileHash -LiteralPath $taskTo).Hash){throw 'Copy hash mismatch'}
}
Copy-Item -LiteralPath (Join-Path $taskSource 'source') -Destination (Join-Path $taskDestination 'source') -Recurse
Copy-Item -LiteralPath (Join-Path $taskSource 'inputs') -Destination (Join-Path $taskDestination 'inputs') -Recurse
foreach($taskFile in @('README.md','PLAN.md')){
  $taskTarget=Join-Path (Split-Path $taskDestination) $taskFile
  $taskTemporary=$taskTarget+'.publish.tmp'
  if(Test-Path -LiteralPath $taskTemporary){throw 'Unexpected temporary publication file'}
  Copy-Item -LiteralPath (Join-Path $taskStudy $taskFile) -Destination $taskTemporary
  Move-Item -LiteralPath $taskTemporary -Destination $taskTarget -Force
}
$taskBytes=(Get-ChildItem -LiteralPath $taskDestination -File -Recurse | Measure-Object Length -Sum).Sum
if($taskBytes -gt 10MB){throw 'Unexpectedly large RAMSES analysis package'}
[pscustomobject]@{path=$taskDestination;bytes=$taskBytes;native_raw_included=$false}|ConvertTo-Json
