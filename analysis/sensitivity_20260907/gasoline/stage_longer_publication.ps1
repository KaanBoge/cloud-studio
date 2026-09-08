$ErrorActionPreference='Stop'
$taskStudy='C:\Users\kaanb\CloudCrushing\sensitivity_20260907'
$taskFrom=Join-Path $taskStudy 'gasoline'
$taskRepo='C:\Users\kaanb\cloud-studio-repo'
$taskTo=Join-Path $taskRepo 'analysis\sensitivity_20260907\gasoline'
$taskNative='\\wsl.localhost\Ubuntu\home\kaan\sensitivity_20260907\gasoline'
$taskAuditHash='3329dc075b9873cd608aa7a0ff9533ed4215c65145cc573c92190b3a23d544ff'
if(@(git -C $taskRepo status --porcelain).Count){throw 'Review existing repo changes before publication'}
if((git -C $taskRepo rev-parse HEAD).Trim() -ne '8964a45421318f7759ab81570a8b2f214cc0781f'){throw 'Unexpected publication base'}
$taskAudit=Get-Content -Raw -LiteralPath (Join-Path $taskNative 'longer_2rank_audit_v1\report.json') | ConvertFrom-Json
if((Get-FileHash -LiteralPath (Join-Path $taskNative 'longer_2rank_audit_v1\report.json')).Hash.ToLower() -ne $taskAuditHash){throw 'Original failed audit changed'}
if($taskAudit.status -ne 'prospective_comparison_failed_needs_review' -or $taskAudit.native_output_count -ne 81 -or $taskAudit.full_science_controls_completed -ne 0){throw 'Wrong diagnostic evidence'}
$taskReview=Get-Content -Raw -LiteralPath (Join-Path $taskFrom 'longer_2rank_review.json') | ConvertFrom-Json
if($taskReview.audit_sha256 -ne $taskAuditHash -or $taskReview.original_test_passed -or $taskReview.failed_comparisons -ne 6 -or !$taskReview.all_dense_memberships_exact){throw 'Review must preserve the failed criterion'}
if((Get-FileHash -LiteralPath (Join-Path $taskFrom 'review_longer.py')).Hash.ToLower() -ne $taskReview.checker_sha256){throw 'Review source differs'}
$taskBundle=Get-Content -Raw -LiteralPath (Join-Path $taskNative 'runner_longer_2rank_v1\bundle.json') | ConvertFrom-Json
foreach($taskFile in $taskBundle.pinned_files.PSObject.Properties){
 $taskPath='\\wsl.localhost\Ubuntu'+$taskFile.Name.Replace('/','\')
 if((Get-FileHash -LiteralPath $taskPath).Hash.ToLower() -ne $taskFile.Value){throw 'Pinned diagnostic dependency changed'}
}
foreach($taskRow in $taskAudit.states){
 $taskPath='\\wsl.localhost\Ubuntu'+$taskRow.path.Replace('/','\')
 if((Get-FileHash -LiteralPath $taskPath).Hash.ToLower() -ne $taskRow.sha256){throw 'Native output changed'}
 foreach($taskSide in $taskRow.sidecars.PSObject.Properties){
  $taskSidePath=Join-Path (Split-Path $taskPath) $taskSide.Name
  if((Get-FileHash -LiteralPath $taskSidePath).Hash.ToLower() -ne $taskSide.Value.sha256){throw 'Native sidecar changed'}
 }
}
function Copy-Atomic([string]$Source,[string]$Target){
 $taskAbsolute=[IO.Path]::GetFullPath($Target)
 if(!$taskAbsolute.StartsWith($taskRepo+'\analysis\',[StringComparison]::OrdinalIgnoreCase)){throw 'Publication target outside analysis'}
 $taskTemp=$taskAbsolute+'.publish.tmp'
 if(Test-Path -LiteralPath $taskTemp){throw 'Existing publication temporary'}
 Copy-Item -LiteralPath $Source -Destination $taskTemp
 if((Get-FileHash -LiteralPath $Source).Hash -ne (Get-FileHash -LiteralPath $taskTemp).Hash){throw 'Copy hash mismatch'}
 Move-Item -LiteralPath $taskTemp -Destination $taskAbsolute -Force
}
if(!(Test-Path -LiteralPath $taskTo)){New-Item -ItemType Directory -Path $taskTo | Out-Null}
$taskNames=@('README.md','VALIDATION.md','LONGER_VALIDATION.md','LONGER_VALIDATION_PLAN.md','LONGER_VALIDATION_PLAN_2RANK.md','longer_2rank_audit.json','longer_2rank_review.json','longer_2rank_bundle.json','repeatability_audit.json','review_longer.py','test_review_longer.py','verify_longer_2rank.py','test_longer_audit.py','gasoline_controls.py','verify_instrumentation_v3.py','longer_checks_v2.py','execution_2rank.py','test_longer_checks_v2.py','test_gasoline.py','stage_longer_publication.ps1')
foreach($taskName in $taskNames){Copy-Atomic (Join-Path $taskFrom $taskName) (Join-Path $taskTo $taskName)}
Copy-Atomic (Join-Path $taskFrom '.gitattributes') (Join-Path $taskTo '.gitattributes')
foreach($taskName in @('README.md','PLAN.md')){Copy-Atomic (Join-Path $taskStudy $taskName) (Join-Path (Split-Path $taskTo) $taskName)}
Copy-Atomic (Join-Path $taskStudy 'analysis_index.md') (Join-Path $taskRepo 'analysis\README.md')
'Staged failure and retention evidence only;44 accepted full controls. No native source, binaries or raw data published.'
