$ErrorActionPreference='Stop'
$taskStudy='C:\Users\kaanb\CloudCrushing\sensitivity_20260907'
$taskSource=Join-Path $taskStudy 'gizmo'
$taskRepo='C:\Users\kaanb\cloud-studio-repo'
$taskTarget=Join-Path $taskRepo 'analysis\sensitivity_20260907\gizmo'
$taskBase='ceffdc9ad3d7f6432054de541e7224c3235f51a1'
if(@(git -C $taskRepo status --porcelain).Count){throw 'Review existing changes before staging'}
if((git -C $taskRepo rev-parse HEAD).Trim() -ne $taskBase){throw 'Unexpected publication base'}
$taskDiagnosis=Get-Content -Raw -LiteralPath (Join-Path $taskSource 'mfv_restart_diagnosis_v1.json') | ConvertFrom-Json
$taskReview=Get-Content -Raw -LiteralPath (Join-Path $taskSource 'mfv_restart_review_v1.json') | ConvertFrom-Json
if((Get-FileHash -LiteralPath (Join-Path $taskSource 'mfv_restart_diagnosis_v1.json')).Hash.ToLower() -ne '88fbb20c30aeab70b9f7dd60638c05a0abcf1afd876ee091a2ebf0ab5e7956b3'){throw 'Diagnosis changed'}
if((Get-FileHash -LiteralPath (Join-Path $taskSource 'mfv_restart_review_v1.json')).Hash.ToLower() -ne '23cf16be3830b7d3a153fb8ae62e67e255cb6a8961b945c25250b09f62aa6f4e'){throw 'Independent review changed'}
if($taskDiagnosis.status -ne 'diagnostic_only_mfv_not_certified' -or $taskReview.diagnosis_sha256 -ne '88fbb20c30aeab70b9f7dd60638c05a0abcf1afd876ee091a2ebf0ab5e7956b3'){throw 'Wrong diagnostic status'}
foreach($taskPair in @(@('diagnose_mfv_restart.py',$taskDiagnosis.script_sha256),@('review_mfv_restart.py',$taskReview.script_sha256))){
 if((Get-FileHash -LiteralPath (Join-Path $taskSource $taskPair[0])).Hash.ToLower() -ne $taskPair[1]){throw 'Evidence script changed'}
}
foreach($taskCase in $taskReview.cases){
 if($taskCase.independently_checked_final_particles -ne 65536 -or $taskCase.checked_native_snapshots.Count -ne 101 -or $taskCase.checked_restarts.Count -ne 8){throw 'Incomplete independent review'}
}
function Copy-Atomic([string]$Source,[string]$Target){
 $taskAbsolute=[IO.Path]::GetFullPath($Target)
 if(!$taskAbsolute.StartsWith($taskRepo+'\analysis\',[StringComparison]::OrdinalIgnoreCase)){throw 'Target outside analysis'}
 $taskTemp=$taskAbsolute+'.publish.tmp'
 if(Test-Path -LiteralPath $taskTemp){throw 'Existing staging temporary'}
 Copy-Item -LiteralPath $Source -Destination $taskTemp
 if((Get-FileHash -LiteralPath $Source).Hash -ne (Get-FileHash -LiteralPath $taskTemp).Hash){throw 'Copy mismatch'}
 Move-Item -LiteralPath $taskTemp -Destination $taskAbsolute -Force
}
$taskFiles=@('README.md','VALIDATION.md','MFV_RESTART_DIAGNOSIS.md','diagnose_mfv_restart.py','review_mfv_restart.py','test_mfv_restart.py','mfv_restart_diagnosis_v1.json','mfv_restart_review_v1.json','stage_mfv_publication.ps1','verify_mfv_publication.ps1','.gitattributes')
foreach($taskName in $taskFiles){Copy-Atomic (Join-Path $taskSource $taskName) (Join-Path $taskTarget $taskName)}
foreach($taskName in @('README.md','PLAN.md')){Copy-Atomic (Join-Path $taskStudy $taskName) (Join-Path (Split-Path $taskTarget) $taskName)}
Copy-Atomic (Join-Path $taskStudy 'analysis_index.md') (Join-Path $taskRepo 'analysis\README.md')
'Staged MFV read-only diagnosis only;44 accepted controls, no native source/binaries/raw or production viewer entries.'
