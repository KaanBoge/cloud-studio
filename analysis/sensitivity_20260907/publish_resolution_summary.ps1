param([ValidateSet('stage','verify')][string]$Mode='stage',[string]$Commit,[long]$WorkflowId)
$ErrorActionPreference='Stop'
$taskRepo='C:\Users\kaanb\cloud-studio-repo'
$taskStudy='C:\Users\kaanb\CloudCrushing\sensitivity_20260907'
$taskBase='be992e8080dddb7e5e5732dd4a7d9126da2ee3a0'
$taskFiles=@('build_resolution_summary.py','test_resolution_summary.py','publish_resolution_summary.ps1','resolution_summary_v1/README.md','resolution_summary_v1/summary.json','resolution_summary_v1/validation.json','README.md','PLAN.md')
$taskCopies=@()
foreach($taskName in $taskFiles){$taskCopies+=,@((Join-Path $taskStudy $taskName),('analysis/sensitivity_20260907/'+$taskName))}
$taskCopies+=,@((Join-Path $taskStudy 'analysis_index.md'),'analysis/README.md')
$taskStatus=@(git -C $taskRepo status --porcelain)
if($LASTEXITCODE -ne 0 -or $taskStatus.Count){throw 'Unexpected working-tree changes'}
$taskSummary=Get-Content -LiteralPath (Join-Path $taskStudy 'resolution_summary_v1/summary.json') -Raw | ConvertFrom-Json
$taskValidation=Get-Content -LiteralPath (Join-Path $taskStudy 'resolution_summary_v1/validation.json') -Raw | ConvertFrom-Json
if($taskSummary.accepted_full_controls -ne 46 -or $taskSummary.accepted_pairs -ne 23 -or $taskSummary.native_states_in_accepted_analysis -ne 4650 -or $taskSummary.new_native_runs -ne 0 -or $taskValidation.unit_tests_passed -ne 12 -or $taskValidation.code_level_pairs_crosschecked -ne 23 -or $taskValidation.status -ne 'passed_report_only_checks'){throw 'Unexpected accepted scope or validation'}
if((Get-FileHash -LiteralPath (Join-Path $taskStudy 'resolution_summary_v1/summary.json')).Hash.ToLower() -ne $taskValidation.summary_sha256){throw 'Summary changed after validation'}
if((Get-FileHash -LiteralPath (Join-Path $taskStudy 'build_resolution_summary.py')).Hash.ToLower() -ne $taskSummary.extractor_sha256){throw 'Extractor changed'}
if((Get-FileHash -LiteralPath (Join-Path $taskStudy 'test_resolution_summary.py')).Hash.ToLower() -ne $taskValidation.test_script_sha256){throw 'Tests changed'}
foreach($taskSource in $taskSummary.sources.PSObject.Properties){
 foreach($taskRoot in @($taskStudy,(Join-Path $taskRepo 'analysis/sensitivity_20260907'))){
  if((Get-FileHash -LiteralPath (Join-Path $taskRoot $taskSource.Name)).Hash.ToLower() -ne $taskSource.Value.sha256){throw ('Source differs locally or in published repository: '+$taskSource.Name)}
 }
}
if($Mode -eq 'stage'){
 if((git -C $taskRepo rev-parse HEAD).Trim() -ne $taskBase){throw 'Unexpected publication base'}
 foreach($taskCopy in $taskCopies){
  $taskTarget=[IO.Path]::GetFullPath((Join-Path $taskRepo $taskCopy[1]))
  if(!$taskTarget.StartsWith($taskRepo+'\analysis\',[StringComparison]::OrdinalIgnoreCase)){throw 'Outside analysis'}
  $taskParent=Split-Path -Parent $taskTarget
  if(!(Test-Path -LiteralPath $taskParent)){New-Item -ItemType Directory -Path $taskParent | Out-Null}
  $taskTemp=$taskTarget+'.publish.tmp'
  if(Test-Path -LiteralPath $taskTemp){throw 'Staging temporary exists'}
  Copy-Item -LiteralPath $taskCopy[0] -Destination $taskTemp
  if((Get-FileHash -LiteralPath $taskCopy[0]).Hash -ne (Get-FileHash -LiteralPath $taskTemp).Hash){throw 'Copy mismatch'}
  Move-Item -LiteralPath $taskTemp -Destination $taskTarget -Force
 }
 $taskLinks=0
 foreach($taskCopy in $taskCopies){
  if(!$taskCopy[1].EndsWith('.md')){continue}
  $taskMarkdown=Get-Content -LiteralPath (Join-Path $taskRepo $taskCopy[1]) -Raw
  foreach($taskMatch in [regex]::Matches($taskMarkdown,'\[[^\]]*\]\(([^)]+)\)')){
   $taskLink=$taskMatch.Groups[1].Value
   if($taskLink -match '^(https?:|#|mailto:)'){continue}
   $taskRelative=($taskLink -split '#',2)[0]
   if(!(Test-Path -LiteralPath (Join-Path (Split-Path -Parent (Join-Path $taskRepo $taskCopy[1])) $taskRelative))){throw ('Missing relative link: '+$taskLink)}
   $taskLinks++
  }
 }
 Write-Output ('Prepared '+$taskCopies.Count+' analysis files; checked '+$taskLinks+' local links and 11 source hashes in both locations. No viewer entries or native runs.');exit
}
$taskProofPath=Join-Path $taskStudy 'resolution_summary_v1/publication.json'
if(Test-Path -LiteralPath $taskProofPath){throw 'Completed proof already exists'}
if($Commit -notmatch '^[0-9a-f]{40}$' -or $Commit -eq $taskBase -or (git -C $taskRepo rev-parse HEAD).Trim() -ne $Commit -or (git -C $taskRepo ls-remote origin refs/heads/main).Split()[0] -ne $Commit){throw 'Expected advanced matching commit'}
$taskRun=Invoke-RestMethod ('https://api.github.com/repos/KaanBoge/cloud-studio/actions/runs/'+$WorkflowId) -Headers @{'User-Agent'='CloudStudio-verification'}
if($taskRun.status -ne 'completed'){Write-Output ('Pages still '+$taskRun.status);exit 2}
if($taskRun.conclusion -ne 'success' -or $taskRun.head_sha -ne $Commit -or $taskRun.name -ne 'pages build and deployment'){throw 'Wrong Pages deployment'}
$taskChanged=@(git -C $taskRepo diff-tree --no-commit-id --name-only -r $Commit)
$taskPaths=@($taskCopies | ForEach-Object {$_[1]})
if($LASTEXITCODE -ne 0 -or @(Compare-Object $taskChanged $taskPaths).Count){throw 'Unexpected changed file set'}
Add-Type -AssemblyName System.Net.Http
$taskClient=[Net.Http.HttpClient]::new();$taskClient.Timeout=[TimeSpan]::FromSeconds(30);$taskChecks=@()
try{foreach($taskFile in $taskChanged){
 $taskUrl='https://kaanboge.github.io/cloud-studio/'+$taskFile+'?v='+$Commit
 $taskBytes=$taskClient.GetByteArrayAsync($taskUrl).GetAwaiter().GetResult()
 $taskHash=([BitConverter]::ToString([Security.Cryptography.SHA256]::HashData($taskBytes))).Replace('-','').ToLower()
 if($taskHash -ne (Get-FileHash -LiteralPath (Join-Path $taskRepo $taskFile)).Hash.ToLower()){throw ('Live mismatch: '+$taskFile)}
 $taskChecks+=[ordered]@{path=$taskFile;url=$taskUrl;bytes=$taskBytes.Length;sha256=$taskHash}
}}finally{$taskClient.Dispose()}
$taskProof=[ordered]@{status='verified_live';verified_at_utc=[DateTime]::UtcNow.ToString('o');commit=$Commit;previous_commit=$taskBase;pages_workflow_id=$WorkflowId;files_verified=$taskChecks.Count;checks=$taskChecks;scope='Report-only consolidation of 23 accepted pairs, 46 controls,4650 native analysis states. No native rerun, raw deletion, acceptance change or viewer entry.'}
$taskTemp=$taskProofPath+'.tmp';if(Test-Path -LiteralPath $taskTemp){throw 'Proof temporary exists'}
[IO.File]::WriteAllText($taskTemp,($taskProof|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
Move-Item -LiteralPath $taskTemp -Destination $taskProofPath
[pscustomobject]$taskProof | Select-Object status,verified_at_utc,commit,pages_workflow_id,files_verified | ConvertTo-Json -Compress
