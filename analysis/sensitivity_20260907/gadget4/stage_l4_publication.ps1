$ErrorActionPreference='Stop'
$taskStudy='C:\Users\kaanb\CloudCrushing\sensitivity_20260907'
$taskFrom=Join-Path $taskStudy 'gadget4'
$taskRepo='C:\Users\kaanb\cloud-studio-repo'
$taskTo=Join-Path $taskRepo 'analysis\sensitivity_20260907\gadget4'
if(@(git -C $taskRepo status --porcelain).Count){throw 'Review existing repo changes first'}
$taskReport=Get-Content -Raw -LiteralPath (Join-Path $taskFrom 'l4_validation.json') | ConvertFrom-Json
$taskBundle=Get-Content -Raw -LiteralPath (Join-Path $taskFrom 'l4_validation_bundle.json') | ConvertFrom-Json
if($taskReport.status -ne 'passed_L4_initial_and_short_evolved_mass_checks' -or $taskReport.full_science_controls_completed -ne 0 -or $taskReport.native_output_count -ne 4 -or $taskReport.cases.Count -ne 2){throw 'Per-level validation incomplete'}
if((Get-FileHash -LiteralPath (Join-Path $taskFrom 'l4_validation_bundle.json')).Hash.ToLower() -ne $taskReport.frozen_bundle_sha256){throw 'Frozen bundle differs'}
if((Get-FileHash -LiteralPath (Join-Path $taskFrom 'gadget_l4_controls.py')).Hash.ToLower() -ne $taskReport.checker_sha256){throw 'Validation source differs'}
foreach($taskFile in $taskBundle.pinned_files.PSObject.Properties){
  $taskPath='\\wsl.localhost\Ubuntu'+$taskFile.Name.Replace('/','\')
  if((Get-FileHash -LiteralPath $taskPath).Hash.ToLower() -ne $taskFile.Value){throw 'Frozen validation dependency changed'}
}
foreach($taskCase in $taskReport.cases){
  if($taskCase.status -ne 'passed_independent_L4_smoke' -or $taskCase.series.Count -ne 2){throw 'Native short control not validated'}
  foreach($taskRow in $taskCase.series){
    $taskPath='\\wsl.localhost\Ubuntu'+$taskRow.snapshot.Replace('/','\')
    if((Get-FileHash -LiteralPath $taskPath).Hash.ToLower() -ne $taskRow.sha256){throw 'Native raw changed after validation'}
    foreach($taskValue in $taskRow.independent_relative_errors.PSObject.Properties){if($taskValue.Value -gt 1e-11){throw 'Independent mass check failed'}}
  }
}
function Copy-Atomic([string]$Source,[string]$Target){
  $taskTemp=$Target+'.publish.tmp'
  if(Test-Path -LiteralPath $taskTemp){throw 'Unexpected publication temporary file'}
  Copy-Item -LiteralPath $Source -Destination $taskTemp
  if((Get-FileHash -LiteralPath $Source).Hash -ne (Get-FileHash -LiteralPath $taskTemp).Hash){throw 'Copy hash mismatch'}
  Move-Item -LiteralPath $taskTemp -Destination $Target -Force
}
$taskNames=@('README.md','VALIDATION.md','L4_VALIDATION.md','gadget_l4_controls.py','test_gadget_l4.py','freeze_l4_validation.py','freeze_l4_validation.v1.py','launch_l4_validation_windows.ps1','l4_validation.json','l4_validation_bundle.json','audit_render_duplicates.py','stage_l4_publication.ps1')
foreach($taskName in $taskNames){Copy-Atomic (Join-Path $taskFrom $taskName) (Join-Path $taskTo $taskName)}
foreach($taskName in @('README.md','PLAN.md')){Copy-Atomic (Join-Path $taskStudy $taskName) (Join-Path (Split-Path $taskTo) $taskName)}
Copy-Atomic (Join-Path $taskStudy 'analysis_index.md') (Join-Path $taskRepo 'analysis\README.md')
'Staged L4 validation and storage evidence only. Full controls remain44; no raw data was deleted or published.'
