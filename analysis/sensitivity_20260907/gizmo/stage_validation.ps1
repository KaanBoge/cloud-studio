$ErrorActionPreference='Stop'
$taskStudy='C:\Users\kaanb\CloudCrushing\sensitivity_20260907'
$taskFrom=Join-Path $taskStudy 'gizmo'
$taskTo='C:\Users\kaanb\cloud-studio-repo\analysis\sensitivity_20260907\gizmo'
if(Test-Path -LiteralPath $taskTo){throw 'Publication folder exists; review rather than overwrite it'}
$taskValidation=Get-Content -Raw -LiteralPath (Join-Path $taskFrom 'verification.json') | ConvertFrom-Json
$taskTiming=Get-Content -Raw -LiteralPath (Join-Path $taskFrom 'snapshot_timing_report.json') | ConvertFrom-Json
if($taskValidation.status -ne 'passed' -or $taskValidation.independent_checks.Count -ne 8 -or $taskTiming.status -ne 'passed' -or $taskTiming.diagnostics.Count -ne 8){throw 'Incomplete validation'}
if((Get-FileHash -LiteralPath (Join-Path $taskFrom 'verify_gizmo.py')).Hash.ToLower() -ne $taskValidation.script_sha256){throw 'Validator hash differs'}
if((Get-FileHash -LiteralPath (Join-Path $taskFrom 'smoke_batch.json')).Hash.ToLower() -ne $taskValidation.smoke_sha256){throw 'Smoke ledger hash differs'}
if((Get-FileHash -LiteralPath (Join-Path $taskFrom 'audit_snapshot_timing.py')).Hash.ToLower() -ne $taskTiming.script_sha256){throw 'Timing script hash differs'}
New-Item -ItemType Directory -Path $taskTo | Out-Null
function Copy-VerifiedAtomic([string]$Source,[string]$Target){
  $taskTemp=$Target+'.publish.tmp'
  if(Test-Path -LiteralPath $taskTemp){throw 'Unexpected publication temporary file'}
  Copy-Item -LiteralPath $Source -Destination $taskTemp
  if((Get-FileHash -LiteralPath $Source).Hash -ne (Get-FileHash -LiteralPath $taskTemp).Hash){throw 'Copy hash mismatch'}
  Move-Item -LiteralPath $taskTemp -Destination $Target -Force
}
$taskFiles=@('README.md','experiment.json','setup_gizmo.py','smoke_gizmo.py','verify_gizmo.py','verify_gizmo.pre_timing.py','audit_snapshot_timing.py','inspect_initial.py','test_smoke_gizmo.py','test_snapshot_timing.py','stage_validation.ps1','build.json','smoke_batch.json','verification.json','snapshot_timing_report.json','initial_recovery_diagnosis.json','generator_sharp.py','generator_historical.py','Config_mfm.sh','Config_mfv.sh','params_mfm_L3.txt','params_mfm_L4.txt','params_mfm_L5.txt','params_mfv_L3.txt','params_mfv_L4.txt','params_mfv_L5.txt')
foreach($taskName in $taskFiles){Copy-VerifiedAtomic (Join-Path $taskFrom $taskName) (Join-Path $taskTo $taskName)}
foreach($taskName in @('README.md','PLAN.md')){Copy-VerifiedAtomic (Join-Path $taskStudy $taskName) (Join-Path (Split-Path $taskTo) $taskName)}
'Staged native GIZMO validation only; no full controls, raw data, native binaries or viewer entries.'
