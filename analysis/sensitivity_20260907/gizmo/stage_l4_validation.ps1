$ErrorActionPreference='Stop'
$taskStudy='C:\Users\kaanb\CloudCrushing\sensitivity_20260907'
$taskFrom=Join-Path $taskStudy 'gizmo'
$taskRepo='C:\Users\kaanb\cloud-studio-repo'
$taskTo=Join-Path $taskRepo 'analysis\sensitivity_20260907\gizmo'
if(@(git -C $taskRepo status --porcelain).Count){throw 'Review existing repo changes before staging'}
$taskV=Get-Content -Raw -LiteralPath (Join-Path $taskFrom 'mfm_l4_validation.json') | ConvertFrom-Json
$taskB=Get-Content -Raw -LiteralPath (Join-Path $taskFrom 'mfm_l4_bundle.json') | ConvertFrom-Json
$taskTests=Get-Content -Raw -LiteralPath (Join-Path $taskFrom 'mfm_l4_tests.json') | ConvertFrom-Json
if($taskV.status -ne 'passed' -or $taskV.level -ne 4 -or $taskV.variant -ne 'mfm' -or $taskV.smokes.Count -ne 2 -or $taskV.diagnostics.Count -ne 4 -or $taskTests.returncode -ne 0){throw 'Incomplete native L4 validation'}
$taskCount=0
foreach($taskCase in ($taskV.smokes+$taskV.diagnostics)){$taskCount+=$taskCase.series.Count}
if($taskCount -ne 16){throw 'Unexpected actual native test count'}
if((Get-FileHash -LiteralPath (Join-Path $taskFrom 'mfm_l4_controls.py')).Hash.ToLower() -ne $taskV.script_sha256){throw 'Native validation script changed'}
foreach($taskFile in $taskB.files.PSObject.Properties){
  if((Get-FileHash -LiteralPath (Join-Path $taskFrom $taskFile.Name)).Hash.ToLower() -ne $taskFile.Value){throw 'Frozen L4 script differs'}
}
if((Get-FileHash -LiteralPath (Join-Path $taskFrom 'mfm_l4_tests.json')).Hash.ToLower() -ne $taskB.tests_sha256){throw 'Frozen L4 tests differ'}
function Copy-VerifiedAtomic([string]$Source,[string]$Target){
  $taskTemp=$Target+'.publish.tmp'
  if(Test-Path -LiteralPath $taskTemp){throw 'Unexpected publication temporary file'}
  Copy-Item -LiteralPath $Source -Destination $taskTemp
  if((Get-FileHash -LiteralPath $Source).Hash -ne (Get-FileHash -LiteralPath $taskTemp).Hash){throw 'Copy hash mismatch'}
  Move-Item -LiteralPath $taskTemp -Destination $Target -Force
}
$taskFiles=@('README.md','L4_VALIDATION_PLAN.md','mfm_l4_controls.py','test_mfm_l4.py','freeze_mfm_l4.py','launch_mfm_l4_windows.ps1','status_mfm_l4.py','mfm_l4_validation.json','mfm_l4_bundle.json','mfm_l4_tests.json','stage_l4_validation.ps1')
foreach($taskFile in $taskFiles){Copy-VerifiedAtomic (Join-Path $taskFrom $taskFile) (Join-Path $taskTo $taskFile)}
foreach($taskFile in @('README.md','PLAN.md')){Copy-VerifiedAtomic (Join-Path $taskStudy $taskFile) (Join-Path (Split-Path $taskTo) $taskFile)}
'Staged L4 validation and launch evidence only. Accepted full-control count remains40.'
