param([ValidateSet('stage','verify')][string]$Mode='stage',[string]$Commit,[long]$WorkflowId)
$ErrorActionPreference='Stop'
$taskStudy='C:\Users\kaanb\CloudCrushing\sensitivity_20260907'
$taskRepo='C:\Users\kaanb\cloud-studio-repo'
$taskGizmo=Join-Path $taskStudy 'gizmo'
$taskEvidence=Join-Path $taskGizmo 'l4_validation_v1'
$taskNative='\\wsl.localhost\Ubuntu\home\kaan\sensitivity_20260907\gizmo\mfv_timestep_repair_v1'
$taskRaw='C:\Users\kaanb\CloudCrushing\native_runs\sensitivity_20260907'
$taskBase='92a9d6352ad84e2cd70f0729854d678d29e9b15d'
$taskEvidenceCopies=@(
 @((Join-Path $taskNative 'l4_prepare_runner_v1\plan.json'),'prepare_plan.json'),
 @((Join-Path $taskNative 'l4_prepare_runner_v1\tests.json'),'prepare_tests.json'),
 @((Join-Path $taskRaw 'mfv_L4_preparation_v1\validation.json'),'validation.json'),
 @((Join-Path $taskNative 'l4_full_runner_v1\plan.json'),'full_plan.json'),
 @((Join-Path $taskNative 'l4_full_runner_v1\tests.json'),'full_tests.json'),
 @((Join-Path $taskRaw 'mfv_L4_preparation_v1\windows_readback.json'),'prepare_windows_readback.json'),
 @((Join-Path $taskRaw 'mfv_L4_velocity_pair_v1\windows_readback.json'),'full_windows_readback.json')
)
if($Mode -eq 'stage'){
 if(Test-Path -LiteralPath $taskEvidence){throw 'Evidence snapshot already exists; do not recreate it'}
 New-Item -ItemType Directory -Path $taskEvidence | Out-Null
 foreach($taskPair in $taskEvidenceCopies){
  $taskTarget=Join-Path $taskEvidence $taskPair[1]
  Copy-Item -LiteralPath $taskPair[0] -Destination $taskTarget
  if((Get-FileHash -LiteralPath $taskPair[0]).Hash -ne (Get-FileHash -LiteralPath $taskTarget).Hash){throw 'Evidence copy differs'}
 }
}
$taskExpected=@{ 'prepare_plan.json'='579f85c2ca74cf7e44a8529b77d3d8f80e45e6760ccc18fa9aad9bae7c15e096'; 'validation.json'='77768badc2721247f471c251ef7e316d02060eabf3e76c549dadcbd367e842c2'; 'full_plan.json'='2b77bb64257e2826dfe241ca6fb31eedcd5b868d73eeb4761cf96ac079430d7c' }
foreach($taskName in $taskExpected.Keys){if((Get-FileHash -LiteralPath (Join-Path $taskEvidence $taskName)).Hash.ToLower() -ne $taskExpected[$taskName]){throw 'Frozen evidence changed'}}
$taskValidation=Get-Content -LiteralPath (Join-Path $taskEvidence 'validation.json') -Raw | ConvertFrom-Json
if($taskValidation.status -ne 'passed_L4_short_preparation_not_full_pair' -or $taskValidation.native_states -ne 16 -or $taskValidation.cases.Count -ne 6 -or $taskValidation.full_controls_added -ne 0){throw 'Wrong validation scope'}
foreach($taskName in @('prepare_tests.json','full_tests.json')){if((Get-Content -Raw -LiteralPath (Join-Path $taskEvidence $taskName)|ConvertFrom-Json).returncode -ne 0){throw 'Failed tests'}}
foreach($taskPlanName in @('prepare_plan.json','full_plan.json')){
 $taskPlan=Get-Content -Raw -LiteralPath (Join-Path $taskEvidence $taskPlanName)|ConvertFrom-Json
 foreach($taskPin in $taskPlan.pins.PSObject.Properties){
  if($taskPin.Name -match '/l4_(prepare|full)_runner_v1/([^/]+\.(py|md))$'){
   if((Get-FileHash -LiteralPath (Join-Path $taskGizmo $Matches[2])).Hash.ToLower() -ne $taskPin.Value){throw 'Custom script differs from executed frozen source'}
  }
 }
}
$taskFiles=@('README.md','PLAN.md','gizmo/README.md','gizmo/MFV_L4_PREPARATION_RESULTS.md','gizmo/MFV_L4_PREPARATION_PLAN.md',
 'gizmo/mfv_l4_prepare.py','gizmo/mfv_l4_native_checks.py','gizmo/test_mfv_l4_prepare.py','gizmo/launch_mfv_l4_prepare.ps1',
 'gizmo/MFV_L4_FULL_PLAN.md','gizmo/mfv_l4_full.py','gizmo/test_mfv_l4_full.py','gizmo/launch_mfv_l4_full.ps1',
 'gizmo/publish_mfv_l4_preparation.ps1')
foreach($taskPair in $taskEvidenceCopies){$taskFiles+=('gizmo/l4_validation_v1/'+$taskPair[1])}
$taskCopies=@()
foreach($taskFile in $taskFiles){$taskCopies+=,@((Join-Path $taskStudy $taskFile),('analysis/sensitivity_20260907/'+$taskFile))}
$taskCopies+=,@((Join-Path $taskStudy 'analysis_index.md'),'analysis/README.md')
if(@(git -C $taskRepo status --porcelain).Count){throw 'Unexpected repository changes'}
if($Mode -eq 'stage'){
 if((git -C $taskRepo rev-parse HEAD).Trim() -ne $taskBase){throw 'Unexpected base'}
 foreach($taskCopy in $taskCopies){
  $taskTarget=[IO.Path]::GetFullPath((Join-Path $taskRepo $taskCopy[1]))
  if(!$taskTarget.StartsWith($taskRepo+'\analysis\',[StringComparison]::OrdinalIgnoreCase)){throw 'Outside analysis'}
  $taskParent=Split-Path -Parent $taskTarget
  if(!(Test-Path -LiteralPath $taskParent)){New-Item -ItemType Directory -Path $taskParent | Out-Null}
  $taskTemp=$taskTarget+'.publish.tmp';if(Test-Path -LiteralPath $taskTemp){throw 'Staging temporary exists'}
  Copy-Item -LiteralPath $taskCopy[0] -Destination $taskTemp
  if((Get-FileHash -LiteralPath $taskCopy[0]).Hash -ne (Get-FileHash -LiteralPath $taskTemp).Hash){throw 'Copy mismatch'}
  Move-Item -LiteralPath $taskTemp -Destination $taskTarget -Force
 }
 $taskLinks=0
 foreach($taskCopy in $taskCopies){
  if(!$taskCopy[1].EndsWith('.md')){continue}
  $taskMarkdown=Get-Content -LiteralPath (Join-Path $taskRepo $taskCopy[1]) -Raw
  foreach($taskMatch in [regex]::Matches($taskMarkdown,'\[[^\]]*\]\(([^)]+)\)')){
   $taskLink=$taskMatch.Groups[1].Value;if($taskLink -match '^(https?:|#|mailto:)'){continue}
   if(!(Test-Path -LiteralPath (Join-Path (Split-Path -Parent (Join-Path $taskRepo $taskCopy[1])) ($taskLink -split '#',2)[0]))){throw ('Missing local link: '+$taskLink)}
   $taskLinks++
  }
 }
 $taskPaths=@($taskCopies|ForEach-Object {$_[1]})
 git -C $taskRepo -c core.autocrlf=false add -- $taskPaths
 if($LASTEXITCODE -ne 0){throw 'Git add failed'}
 foreach($taskCopy in $taskCopies){if((git -C $taskRepo hash-object --no-filters $taskCopy[0]).Trim() -ne (git -C $taskRepo rev-parse (':'+$taskCopy[1])).Trim()){throw 'Staged bytes changed'}}
 git -C $taskRepo -c core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol diff --cached --check
 if($LASTEXITCODE -ne 0 -or @(Compare-Object @(git -C $taskRepo diff --cached --name-only) $taskPaths).Count){throw 'Invalid staged scope/whitespace'}
 Write-Output ('Staged '+$taskPaths.Count+' checked custom files; '+$taskLinks+' local links. No native full completion or viewer entry claimed.');exit
}
$taskProof=Join-Path $taskEvidence 'publication.json';if(Test-Path -LiteralPath $taskProof){throw 'Completed proof exists'}
if($Commit -notmatch '^[0-9a-f]{40}$' -or $Commit -eq $taskBase -or (git -C $taskRepo rev-parse HEAD).Trim() -ne $Commit -or (git -C $taskRepo ls-remote origin refs/heads/main).Split()[0] -ne $Commit){throw 'Expected advanced matching commit'}
$taskRun=Invoke-RestMethod ('https://api.github.com/repos/KaanBoge/cloud-studio/actions/runs/'+$WorkflowId) -Headers @{'User-Agent'='CloudStudio-verification'}
if($taskRun.status -ne 'completed'){Write-Output ('Pages still '+$taskRun.status);exit 2}
if($taskRun.conclusion -ne 'success' -or $taskRun.head_sha -ne $Commit -or $taskRun.name -ne 'pages build and deployment'){throw 'Wrong Pages deployment'}
$taskChanged=@(git -C $taskRepo diff-tree --no-commit-id --name-only -r $Commit)
if(@(Compare-Object $taskChanged @($taskCopies|ForEach-Object {$_[1]})).Count){throw 'Unexpected changed paths'}
Add-Type -AssemblyName System.Net.Http
$taskClient=[Net.Http.HttpClient]::new();$taskClient.Timeout=[TimeSpan]::FromSeconds(30);$taskChecks=@()
try{foreach($taskFile in $taskChanged){
 $taskUrl='https://kaanboge.github.io/cloud-studio/'+$taskFile+'?v='+$Commit
 $taskBytes=$taskClient.GetByteArrayAsync($taskUrl).GetAwaiter().GetResult()
 $taskHash=([BitConverter]::ToString([Security.Cryptography.SHA256]::HashData($taskBytes))).Replace('-','').ToLower()
 if($taskHash -ne (Get-FileHash -LiteralPath (Join-Path $taskRepo $taskFile)).Hash.ToLower()){throw ('Live byte mismatch '+$taskFile)}
 $taskChecks+=[ordered]@{path=$taskFile;url=$taskUrl;bytes=$taskBytes.Length;sha256=$taskHash}
}}finally{$taskClient.Dispose()}
$taskResult=[ordered]@{status='verified_live';verified_at_utc=[DateTime]::UtcNow.ToString('o');commit=$Commit;previous_commit=$taskBase;pages_workflow_id=$WorkflowId;files_verified=$taskChecks.Count;checks=$taskChecks;scope='Six repaired MFV L4 short diagnostics,16states,48restart files; full pair launched but not yet accepted. Study count48. No raw deletion or production viewer entries.'}
[IO.File]::WriteAllText($taskProof,($taskResult|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
[pscustomobject]$taskResult | Select-Object status,verified_at_utc,commit,pages_workflow_id,files_verified | ConvertTo-Json -Compress
