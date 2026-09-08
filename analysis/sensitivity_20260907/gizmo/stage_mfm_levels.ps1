$ErrorActionPreference='Stop'
$taskStudy='C:\Users\kaanb\CloudCrushing\sensitivity_20260907'
$taskFrom=Join-Path $taskStudy 'gizmo'
$taskRepo='C:\Users\kaanb\cloud-studio-repo'
$taskTo=Join-Path $taskRepo 'analysis\sensitivity_20260907\gizmo'
if(@(git -C $taskRepo status --porcelain).Count){throw 'Review existing repo changes before staging'}
$taskReport=Get-Content -Raw -LiteralPath (Join-Path $taskFrom 'mfm_levels_report.json') | ConvertFrom-Json
$taskBatch=Get-Content -Raw -LiteralPath (Join-Path $taskFrom 'mfm_l4_batch.json') | ConvertFrom-Json
if($taskReport.status -ne 'share_with_caveats' -or $taskReport.controls -ne 4 -or $taskReport.new_level4_controls -ne 2 -or $taskReport.native_states -ne 404 -or $taskBatch.status -ne 'complete_independent_checks' -or $taskBatch.finished.Count -ne 2){throw 'Incomplete native pairs/analysis'}
function Assert-Hash([string]$Name,[string]$Expected){
  if((Get-FileHash -LiteralPath (Join-Path $taskFrom $Name)).Hash.ToLower() -ne $Expected){throw "Provenance mismatch: $Name"}
}
Assert-Hash 'analyze_mfm_levels.py' $taskReport.analysis_sha256
Assert-Hash 'mass_mfm_L3_L4.png' $taskReport.plot_sha256
foreach($taskSource in $taskReport.source_batches){
  $taskFile=switch($taskSource.level){3{'full_l3_batch.json'} 4{'mfm_l4_batch.json'} default{throw 'Unknown native level'}}
  Assert-Hash $taskFile $taskSource.sha256
}
foreach($taskCase in $taskReport.cases){
  if($taskCase.cadence.native_snapshots -ne 101 -or $taskCase.independent_max_relative_mass_error -gt 1e-11 -or $taskCase.direct_mass_recheck_max_relative_error -gt 1e-12){throw 'Native case failed analysis checks'}
}
function Copy-VerifiedAtomic([string]$Source,[string]$Target){
  $taskTemp=$Target+'.publish.tmp'
  if(Test-Path -LiteralPath $taskTemp){throw 'Unexpected publication temporary file'}
  Copy-Item -LiteralPath $Source -Destination $taskTemp
  if((Get-FileHash -LiteralPath $Source).Hash -ne (Get-FileHash -LiteralPath $taskTemp).Hash){throw 'Copy hash mismatch'}
  Move-Item -LiteralPath $taskTemp -Destination $Target -Force
}
$taskFiles=@('README.md','VALIDATION.md','MFM_LEVELS_VALIDATION.md','analyze_mfm_levels.py','test_mfm_levels_analysis.py','stage_mfm_levels.ps1','mfm_l4_batch.json','mfm_levels_report.json','mass_mfm_L3_L4.png')
foreach($taskName in $taskFiles){Copy-VerifiedAtomic (Join-Path $taskFrom $taskName) (Join-Path $taskTo $taskName)}
foreach($taskName in @('README.md','PLAN.md')){Copy-VerifiedAtomic (Join-Path $taskStudy $taskName) (Join-Path (Split-Path $taskTo) $taskName)}
Copy-VerifiedAtomic (Join-Path $taskStudy 'analysis_index.md') (Join-Path $taskRepo 'analysis\README.md')
'Staged4 accepted MFM L3/L4 controls,404 native diagnostic states and resolution overlay. MFV failures remain separate. Native raw is retained, not published.'
