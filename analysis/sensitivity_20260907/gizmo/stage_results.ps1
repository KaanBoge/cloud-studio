$ErrorActionPreference='Stop'
$taskStudy='C:\Users\kaanb\CloudCrushing\sensitivity_20260907'
$taskFrom=Join-Path $taskStudy 'gizmo'
$taskRepo='C:\Users\kaanb\cloud-studio-repo'
$taskTo=Join-Path $taskRepo 'analysis\sensitivity_20260907\gizmo'
if(!(Test-Path -LiteralPath $taskTo)){throw 'Existing validated GIZMO publication required'}
if(@(git -C $taskRepo status --porcelain).Count -ne 0){throw 'Review existing repo changes before staging'}
$taskReport=Get-Content -Raw -LiteralPath (Join-Path $taskFrom 'mfm_l3_report.json') | ConvertFrom-Json
$taskQA=Get-Content -Raw -LiteralPath (Join-Path $taskFrom 'delivery_validation.json') | ConvertFrom-Json
$taskAudit=Get-Content -Raw -LiteralPath (Join-Path $taskFrom 'mfv_pair_audit.json') | ConvertFrom-Json
$taskBundle=Get-Content -Raw -LiteralPath (Join-Path $taskFrom 'full_l3_bundle.json') | ConvertFrom-Json
if($taskReport.controls -ne 2 -or $taskReport.level -ne 3 -or $taskReport.code -ne 'GIZMO MFM' -or $taskQA.mfm_native_states_rechecked -ne 202 -or $taskQA.mfv_failed_controls -ne 2 -or $taskAudit.status -ne 'needs_review_not_certified'){throw 'Unexpected science/QA status'}
function Assert-Hash([string]$Name,[string]$Expected){
  if((Get-FileHash -LiteralPath (Join-Path $taskFrom $Name)).Hash.ToLower() -ne $Expected){throw "Provenance mismatch: $Name"}
}
Assert-Hash 'mfm_l3_report.json' $taskQA.mfm_report_sha256
Assert-Hash 'mass_mfm_L3.png' $taskQA.mfm_plot_sha256
Assert-Hash 'full_l3_batch.json' $taskQA.batch_sha256
Assert-Hash 'mfv_pair_audit.json' $taskQA.mfv_audit_sha256
Assert-Hash 'analyze_mfm_l3.py' $taskReport.analysis_sha256
Assert-Hash 'audit_mfv_pair.py' $taskAudit.script_sha256
Assert-Hash 'validate_results.py' $taskQA.script_sha256
Assert-Hash 'full_l3_preflight.json' $taskBundle.preflight_sha256
Assert-Hash 'full_l3_tests.json' $taskBundle.tests_sha256
foreach($taskProperty in $taskBundle.files.PSObject.Properties){Assert-Hash $taskProperty.Name $taskProperty.Value}
function Copy-VerifiedAtomic([string]$Source,[string]$Target){
  $taskTemp=$Target+'.publish.tmp'
  if(Test-Path -LiteralPath $taskTemp){throw 'Unexpected publication temporary file'}
  Copy-Item -LiteralPath $Source -Destination $taskTemp
  if((Get-FileHash -LiteralPath $Source).Hash -ne (Get-FileHash -LiteralPath $taskTemp).Hash){throw 'Copy hash mismatch'}
  Move-Item -LiteralPath $taskTemp -Destination $Target -Force
}
$taskFiles=@('README.md','VALIDATION.md','run_full_l3.py','test_full_l3.py','freeze_full_l3.py','launch_full_l3_windows.ps1','run_mfv_failure_control.py','launch_mfv_failure_control.ps1','inspect_mfv_fields.py','audit_mfv_pair.py','analyze_mfm_l3.py','validate_results.py','stage_results.ps1','full_l3_bundle.json','full_l3_preflight.json','full_l3_tests.json','full_l3_batch.json','mfv_failure_control.json','mfv_field_audit.json','mfv_pair_audit.json','mfm_l3_report.json','mass_mfm_L3.png','delivery_validation.json')
foreach($taskName in $taskFiles){Copy-VerifiedAtomic (Join-Path $taskFrom $taskName) (Join-Path $taskTo $taskName)}
foreach($taskName in @('README.md','PLAN.md')){Copy-VerifiedAtomic (Join-Path $taskStudy $taskName) (Join-Path (Split-Path $taskTo) $taskName)}
Copy-VerifiedAtomic (Join-Path $taskStudy 'analysis_index.md') (Join-Path $taskRepo 'analysis\README.md')
'Staged accepted MFM L3 results and separately labeled MFV failure evidence. No native binaries, solver C sources, raw datasets or production viewer entries.'
