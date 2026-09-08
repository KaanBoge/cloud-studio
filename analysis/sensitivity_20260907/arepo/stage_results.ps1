$ErrorActionPreference='Stop'
$taskStudy='C:\Users\kaanb\CloudCrushing\sensitivity_20260907'
$taskFrom=Join-Path $taskStudy 'arepo'
$taskTo='C:\Users\kaanb\cloud-studio-repo\analysis\sensitivity_20260907\arepo'
$taskReport=Get-Content -LiteralPath (Join-Path $taskFrom 'report.json') -Raw | ConvertFrom-Json
$taskBatch=Get-Content -LiteralPath (Join-Path $taskFrom 'batch.json') -Raw | ConvertFrom-Json
if($taskReport.status -ne 'share_with_caveats' -or $taskBatch.finished.Count -ne 4 -or $taskReport.pairs.Count -ne 2){throw 'Unexpected completed scope'}
if((Get-FileHash -LiteralPath (Join-Path $taskFrom 'batch.json')).Hash.ToLower() -ne $taskReport.batch_sha256){throw 'Report/batch hash mismatch'}
if((Get-FileHash -LiteralPath (Join-Path $taskFrom 'analyze_arepo.py')).Hash.ToLower() -ne $taskReport.analysis_sha256){throw 'Analysis script hash mismatch'}
foreach($taskCase in $taskBatch.finished){
  if($taskCase.status -ne 'complete_native_checks' -or $taskCase.unique_snapshots -ne 101 -or $taskCase.series.Count -ne 101){throw 'Incomplete native case'}
  $taskLast=-1.0
  foreach($taskRow in $taskCase.series){
    if($null -eq $taskRow.t_over_tcc -or [double]::IsNaN($taskRow.t_over_tcc) -or [double]::IsInfinity($taskRow.t_over_tcc) -or $taskRow.t_over_tcc -le $taskLast){throw 'Invalid native times'}
    $taskLast=$taskRow.t_over_tcc
  }
  if($taskCase.series[0].t_over_tcc -ne 0 -or $taskLast -ne 5){throw 'Incomplete time coverage'}
}
foreach($taskPair in $taskReport.pairs){
  if($taskPair.frames_per_variant.Count -ne 2 -or ($taskPair.frames_per_variant | Where-Object {$_ -ne 101}) -or $taskPair.independent_max_relative_mass_error -gt 1e-11){throw 'Incomplete or unverified states'}
}
function Copy-VerifiedAtomic([string]$Source,[string]$Target){
  $taskTemp=$Target+'.publish.tmp'
  if(Test-Path -LiteralPath $taskTemp){throw 'Unexpected publication temporary file'}
  Copy-Item -LiteralPath $Source -Destination $taskTemp
  if((Get-FileHash -LiteralPath $Source).Hash -ne (Get-FileHash -LiteralPath $taskTemp).Hash){throw 'Copy hash mismatch'}
  Move-Item -LiteralPath $taskTemp -Destination $Target -Force
}
foreach($taskName in @('README.md','VALIDATION.md','report.json','mass_and_retention.png','batch.json','stage_results.ps1')){
  Copy-VerifiedAtomic (Join-Path $taskFrom $taskName) (Join-Path $taskTo $taskName)
}
foreach($taskName in @('README.md','PLAN.md')){
  Copy-VerifiedAtomic (Join-Path $taskStudy $taskName) (Join-Path (Split-Path $taskTo) $taskName)
}
Copy-VerifiedAtomic (Join-Path $taskStudy 'analysis_index.md') 'C:\Users\kaanb\cloud-studio-repo\analysis\README.md'
'Staged 404 independently checked Arepo states and analysis, not raw datasets or viewer entries.'
