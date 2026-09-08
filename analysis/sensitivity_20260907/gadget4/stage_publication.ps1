$ErrorActionPreference='Stop'
$taskStudy='C:\Users\kaanb\CloudCrushing\sensitivity_20260907'
$taskFrom=Join-Path $taskStudy 'gadget4'
$taskRepo='C:\Users\kaanb\cloud-studio-repo'
$taskTo=Join-Path $taskRepo 'analysis\sensitivity_20260907\gadget4'
if(@(git -C $taskRepo status --porcelain).Count){throw 'Review existing repo changes first'}
$taskReport=Get-Content -Raw -LiteralPath (Join-Path $taskFrom 'l3_report.json') | ConvertFrom-Json
$taskBatch=Get-Content -Raw -LiteralPath (Join-Path $taskFrom 'full_l3_batch.json') | ConvertFrom-Json
if($taskReport.status -ne 'share_with_caveats' -or $taskReport.controls -ne 2 -or $taskReport.native_states -ne 202 -or $taskBatch.status -ne 'complete_independent_checks' -or $taskBatch.finished.Count -ne 2){throw 'Full native analysis is not complete'}
function Assert-Hash([string]$Name,[string]$Expected){if((Get-FileHash -LiteralPath (Join-Path $taskFrom $Name)).Hash.ToLower() -ne $Expected){throw "Source hash mismatch: $Name"}}
Assert-Hash 'analyze_l3.py' $taskReport.analysis_sha256
Assert-Hash 'mass_L3.png' $taskReport.plot_sha256
Assert-Hash 'full_l3_batch.json' $taskReport.batch_sha256
foreach($taskCase in $taskReport.cases){if($taskCase.cadence.native_snapshots -ne 101 -or $taskCase.independent_max_relative_mass_error -gt 1e-11 -or $taskCase.cadence.exact_scheduler_max_absolute_error -gt $taskCase.cadence.roundoff_bound){throw 'Native field or time checks failed'}}
New-Item -ItemType Directory -Path $taskTo -Force | Out-Null
function Copy-Atomic([string]$Source,[string]$Target){
  $taskTemp=$Target+'.publish.tmp'
  if(Test-Path -LiteralPath $taskTemp){throw 'Unexpected temporary publication file'}
  Copy-Item -LiteralPath $Source -Destination $taskTemp
  if((Get-FileHash -LiteralPath $Source).Hash -ne (Get-FileHash -LiteralPath $taskTemp).Hash){throw 'Copy hash mismatch'}
  Move-Item -LiteralPath $taskTemp -Destination $Target -Force
}
$taskNames=@('README.md','VALIDATION.md','experiment.json','gadget_controls.py','test_gadget_controls.py','verify_gadget.py','verify_gadget.v1.py','test_verify_gadget.py','run_full_l3.py','run_full_l3_v2.py','test_full_l3.py','native_cadence.py','test_native_cadence.py','audit_native_times.py','freeze_full_l3.py','freeze_full_l3_v2.py','launch_smokes_windows.ps1','launch_full_l3_windows.ps1','launch_full_l3_v2_windows.ps1','analyze_l3.py','test_analysis.py','stage_publication.ps1','build.json','smoke_batch.json','verification_v2.json','full_l3_bundle.json','full_l3_v2_bundle.json','native_cadence_audit.json','l3_report.json','mass_L3.png','full_l3_batch.json','original_stopped_batch.json','Config.sh','params_L3.txt','params_L4.txt')
foreach($taskName in $taskNames){Copy-Atomic (Join-Path $taskFrom $taskName) (Join-Path $taskTo $taskName)}
foreach($taskName in @('README.md','PLAN.md')){Copy-Atomic (Join-Path $taskStudy $taskName) (Join-Path (Split-Path $taskTo) $taskName)}
Copy-Atomic (Join-Path $taskStudy 'analysis_index.md') (Join-Path $taskRepo 'analysis\README.md')
"Prepared $($taskNames.Count) Gadget-4 artifacts and three overview docs. All native raw retained locally."
