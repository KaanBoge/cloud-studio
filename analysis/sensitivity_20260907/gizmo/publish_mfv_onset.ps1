param([ValidateSet('stage','verify')][string]$Mode='stage',[string]$Commit,[long]$WorkflowId)
$ErrorActionPreference='Stop'
$taskRepo='C:\Users\kaanb\cloud-studio-repo'
$taskStudy='C:\Users\kaanb\CloudCrushing\sensitivity_20260907'
$taskFrom=Join-Path $taskStudy 'gizmo'
$taskBase='b985e49f4171ae30105826ba3f62d7bc870334f5'
$taskFiles=@('README.md','.gitattributes','MFV_SHORT_VALIDATION.md','MFV_ONSET_VALIDATION.md','MFV_ONSET_PLAN.md','MFV_ONSET_CLOCK_REVIEW.md','mfv_onset.py','test_mfv_onset.py','review_mfv_onset.py','test_mfv_onset_clock.py','review_mfv_onset_v2.py','test_mfv_onset_clock_v2.py','onset_plan.json','onset_native_result.json','onset_initial_validation.json','onset_clock_review.json','publish_mfv_onset.ps1')
$taskCopies=@()
foreach($taskFile in $taskFiles){$taskCopies+=,@((Join-Path $taskFrom $taskFile),('analysis/sensitivity_20260907/gizmo/'+$taskFile))}
foreach($taskFile in @('README.md','PLAN.md')){$taskCopies+=,@((Join-Path $taskStudy $taskFile),('analysis/sensitivity_20260907/'+$taskFile))}
$taskCopies+=,@((Join-Path $taskStudy 'analysis_index.md'),'analysis/README.md')
$taskStatus=@(git -C $taskRepo status --porcelain)
if($LASTEXITCODE -ne 0 -or $taskStatus.Count){throw 'Review unexpected working-tree state first'}
if($Mode -eq 'stage'){
 if((git -C $taskRepo rev-parse HEAD).Trim() -ne $taskBase){throw 'Unexpected publication base'}
 $taskExpected=@{'onset_clock_review.json'='53d8f951fabe54ec48795a626be1a55d27a48e25192d5021dd705f7ce95cfb5f';'onset_native_result.json'='6655b288479c721aa01acc5c84ba0c72b47511c9cfde0c4fcf0dcc1fb9715e01';'onset_plan.json'='52c8ecbea186266d336652bcd0ad4d465de3b2a0a8a19b13880f126e027998ce';'onset_initial_validation.json'='d1da6d9d1e5b356fb1dd10e8f34931f316e51529a4865a72442f5757dd7a1d76'}
 foreach($taskName in $taskExpected.Keys){if((Get-FileHash -LiteralPath (Join-Path $taskFrom $taskName)).Hash.ToLower() -ne $taskExpected[$taskName]){throw 'Changed onset evidence'}}
 $taskValidation=Get-Content -Raw -LiteralPath (Join-Path $taskFrom 'onset_clock_review.json') | ConvertFrom-Json
 if($taskValidation.status -ne 'passed_onset_diagnostic_not_full_pair' -or $taskValidation.native_frames -ne 101 -or $taskValidation.clock.bits -ne 60 -or !$taskValidation.mass_account.passes -or $taskValidation.accepted_full_controls -ne 44 -or $taskValidation.completed_full_controls_added -ne 0){throw 'Wrong onset-validation status'}
 if((Get-FileHash -LiteralPath (Join-Path $taskFrom 'review_mfv_onset_v2.py')).Hash.ToLower() -ne $taskValidation.script_sha256){throw 'Reviewed correction script changed'}
 if((Get-FileHash -LiteralPath (Join-Path $taskFrom 'MFV_ONSET_CLOCK_REVIEW.md')).Hash.ToLower() -ne $taskValidation.protocol_sha256){throw 'Correction protocol changed'}
 $taskPlan=Get-Content -Raw -LiteralPath (Join-Path $taskFrom 'onset_plan.json') | ConvertFrom-Json
 foreach($taskProperty in $taskPlan.files.PSObject.Properties){if((Get-FileHash -LiteralPath (Join-Path $taskFrom $taskProperty.Name)).Hash.ToLower() -ne $taskProperty.Value){throw 'Frozen helper differs from reviewed source'}}
 foreach($taskCopy in $taskCopies){
  $taskTarget=[IO.Path]::GetFullPath((Join-Path $taskRepo $taskCopy[1]))
  if(!$taskTarget.StartsWith($taskRepo+'\analysis\',[StringComparison]::OrdinalIgnoreCase)){throw 'Outside analysis'}
  $taskTemp=$taskTarget+'.publish.tmp'
  if(Test-Path -LiteralPath $taskTemp){throw 'Existing staging temporary'}
  Copy-Item -LiteralPath $taskCopy[0] -Destination $taskTemp
  if((Get-FileHash -LiteralPath $taskCopy[0]).Hash -ne (Get-FileHash -LiteralPath $taskTemp).Hash){throw 'Copy differs'}
  Move-Item -LiteralPath $taskTemp -Destination $taskTarget -Force
 }
 'Prepared20 custom analysis files only; native data and accepted count unchanged.'
 exit
}
$taskProofPath=Join-Path $taskFrom 'mfv_onset_publication.json'
if(Test-Path -LiteralPath $taskProofPath){throw 'Completed publication proof exists'}
if($Commit -notmatch '^[0-9a-f]{40}$' -or $Commit -eq $taskBase -or (git -C $taskRepo rev-parse HEAD).Trim() -ne $Commit -or (git -C $taskRepo ls-remote origin refs/heads/main).Split()[0] -ne $Commit){throw 'Expected advanced matching commit'}
$taskRun=Invoke-RestMethod ('https://api.github.com/repos/KaanBoge/cloud-studio/actions/runs/'+$WorkflowId) -Headers @{'User-Agent'='CloudStudio-verification'}
if($taskRun.status -ne 'completed'){Write-Output ('Pages still '+$taskRun.status);exit 2}
if($taskRun.conclusion -ne 'success' -or $taskRun.head_sha -ne $Commit -or $taskRun.name -ne 'pages build and deployment'){throw 'Wrong Pages deployment'}
$taskChanged=@(git -C $taskRepo diff-tree --no-commit-id --name-only -r $Commit)
if($LASTEXITCODE -ne 0 -or $taskChanged.Count -ne 20){throw 'Unexpected publication file count'}
$taskPaths=@($taskCopies | ForEach-Object {$_[1]})
if(@(Compare-Object $taskChanged $taskPaths).Count){throw 'Unexpected publication paths'}
Add-Type -AssemblyName System.Net.Http
$taskClient=[Net.Http.HttpClient]::new()
$taskClient.Timeout=[TimeSpan]::FromSeconds(30)
$taskChecks=@()
try{foreach($taskFile in $taskChanged){
 $taskSurface='live_pages'
 $taskUrl='https://kaanboge.github.io/cloud-studio/'+$taskFile+'?v='+$Commit
 if($taskFile.EndsWith('/.gitattributes')){$taskSurface='repository_config';$taskUrl='https://raw.githubusercontent.com/KaanBoge/cloud-studio/'+$Commit+'/'+$taskFile}
 $taskBytes=$taskClient.GetByteArrayAsync($taskUrl).GetAwaiter().GetResult()
 $taskHash=([BitConverter]::ToString([Security.Cryptography.SHA256]::HashData($taskBytes))).Replace('-','').ToLower()
 if($taskHash -ne (Get-FileHash -LiteralPath (Join-Path $taskRepo $taskFile)).Hash.ToLower()){throw ('Live bytes differ: '+$taskFile)}
 $taskChecks+=[ordered]@{path=$taskFile;surface=$taskSurface;url=$taskUrl;bytes=$taskBytes.Length;sha256=$taskHash}
}}finally{$taskClient.Dispose()}
$taskProof=[ordered]@{status='verified_live';verified_at_utc=[DateTime]::UtcNow.ToString('o');commit=$Commit;previous_commit=$taskBase;pages_workflow_id=$WorkflowId;pages_conclusion=$taskRun.conclusion;files_verified=@($taskChecks | Where-Object {$_.surface -eq 'live_pages'}).Count;checks=$taskChecks;scope='101 native repaired historical MFV diagnostic states through5tcc pass field and combined mass-ledger checks. Source-derived clock and JSON reporting corrections disclosed; no rerun. Not an accepted velocity pair; accepted full controls remain44. All raw retained.'}
$taskTemp=$taskProofPath+'.tmp'
if(Test-Path -LiteralPath $taskTemp){throw 'Existing proof temporary'}
[IO.File]::WriteAllText($taskTemp,($taskProof|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
Move-Item -LiteralPath $taskTemp -Destination $taskProofPath
[pscustomobject]$taskProof | Select-Object status,verified_at_utc,commit,pages_workflow_id,files_verified | ConvertTo-Json -Compress
