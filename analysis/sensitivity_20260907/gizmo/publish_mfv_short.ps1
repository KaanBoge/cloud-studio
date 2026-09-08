param([ValidateSet('stage','verify')][string]$Mode='stage',[string]$Commit,[long]$WorkflowId)
$ErrorActionPreference='Stop'
$taskRepo='C:\Users\kaanb\cloud-studio-repo'
$taskStudy='C:\Users\kaanb\CloudCrushing\sensitivity_20260907'
$taskFrom=Join-Path $taskStudy 'gizmo'
$taskBase='be70fb1e6f47dfad8775adf7ac9c5d83f8fee010'
$taskFiles=@('README.md','.gitattributes','MFV_SHORT_VALIDATION.md','MFV_SHORT_VALIDATION_PLAN.md','mfv_short_controls.py','test_mfv_short.py','storage_guard.py','mfv_short_plan.json','mfv_short_batch.json','mfv_short_validation.json','MFV_REPAIR_BUILD_VALIDATION.md','publish_mfv_short.ps1')
$taskCopies=@()
foreach($taskFile in $taskFiles){$taskCopies+=,@((Join-Path $taskFrom $taskFile),('analysis/sensitivity_20260907/gizmo/'+$taskFile))}
foreach($taskFile in @('README.md','PLAN.md')){$taskCopies+=,@((Join-Path $taskStudy $taskFile),('analysis/sensitivity_20260907/'+$taskFile))}
$taskCopies+=,@((Join-Path $taskStudy 'analysis_index.md'),'analysis/README.md')
$taskStatus=@(git -C $taskRepo status --porcelain)
if($LASTEXITCODE -ne 0 -or $taskStatus.Count){throw 'Review unexpected working-tree state first'}
if($Mode -eq 'stage'){
 if((git -C $taskRepo rev-parse HEAD).Trim() -ne $taskBase){throw 'Unexpected publication base'}
 $taskExpected=@{'mfv_short_validation.json'='1a454241ada059c40994ecc0cde6e2a774fbd7f0ed6d8a608419739188019cc6';'mfv_short_batch.json'='f59689b825fe06d526d171aa7b98bca1a0fef55ccc7ada0db626ae24d389843a';'mfv_short_plan.json'='73aecfe271c30300a2d3ebe0c547791dc17e310b3f7727f876ca238598df01e9'}
 foreach($taskName in $taskExpected.Keys){if((Get-FileHash -LiteralPath (Join-Path $taskFrom $taskName)).Hash.ToLower() -ne $taskExpected[$taskName]){throw 'Changed short-test evidence'}}
 $taskValidation=Get-Content -Raw -LiteralPath (Join-Path $taskFrom 'mfv_short_validation.json') | ConvertFrom-Json
 if($taskValidation.status -ne 'passed_short_native_gates_not_full_science' -or $taskValidation.failures.Count -ne 0 -or $taskValidation.cases.Count -ne 2 -or $taskValidation.accepted_full_controls -ne 44 -or $taskValidation.completed_full_controls_added -ne 0){throw 'Wrong short-validation status'}
 if(@($taskValidation.cases | ForEach-Object {$_.outputs}).Count -ne 4){throw 'Wrong diagnostic output count'}
 $taskPlan=Get-Content -Raw -LiteralPath (Join-Path $taskFrom 'mfv_short_plan.json') | ConvertFrom-Json
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
 'Prepared15 custom analysis files only; native data and accepted count unchanged.'
 exit
}
$taskProofPath=Join-Path $taskFrom 'mfv_short_publication.json'
if(Test-Path -LiteralPath $taskProofPath){throw 'Completed publication proof exists'}
if($Commit -notmatch '^[0-9a-f]{40}$' -or $Commit -eq $taskBase -or (git -C $taskRepo rev-parse HEAD).Trim() -ne $Commit -or (git -C $taskRepo ls-remote origin refs/heads/main).Split()[0] -ne $Commit){throw 'Expected advanced matching commit'}
$taskRun=Invoke-RestMethod ('https://api.github.com/repos/KaanBoge/cloud-studio/actions/runs/'+$WorkflowId) -Headers @{'User-Agent'='CloudStudio-verification'}
if($taskRun.status -ne 'completed'){Write-Output ('Pages still '+$taskRun.status);exit 2}
if($taskRun.conclusion -ne 'success' -or $taskRun.head_sha -ne $Commit -or $taskRun.name -ne 'pages build and deployment'){throw 'Wrong Pages deployment'}
$taskChanged=@(git -C $taskRepo diff-tree --no-commit-id --name-only -r $Commit)
if($LASTEXITCODE -ne 0 -or $taskChanged.Count -ne 15){throw 'Unexpected publication file count'}
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
$taskProof=[ordered]@{status='verified_live';verified_at_utc=[DateTime]::UtcNow.ToString('o');commit=$Commit;previous_commit=$taskBase;pages_workflow_id=$WorkflowId;pages_conclusion=$taskRun.conclusion;files_verified=@($taskChecks | Where-Object {$_.surface -eq 'live_pages'}).Count;checks=$taskChecks;scope='Four short native MFV diagnostic outputs: reference exact versus retained old outputs, repaired mass response and combined mass accounting pass. Not late-failure validation; accepted full controls remain44. All raw retained.'}
$taskTemp=$taskProofPath+'.tmp'
if(Test-Path -LiteralPath $taskTemp){throw 'Existing proof temporary'}
[IO.File]::WriteAllText($taskTemp,($taskProof|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
Move-Item -LiteralPath $taskTemp -Destination $taskProofPath
[pscustomobject]$taskProof | Select-Object status,verified_at_utc,commit,pages_workflow_id,files_verified | ConvertTo-Json -Compress
