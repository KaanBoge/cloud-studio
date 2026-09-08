param([ValidateSet('stage','verify')][string]$Mode='stage',[string]$Commit,[long]$WorkflowId)
$ErrorActionPreference='Stop'
$taskRepo='C:\Users\kaanb\cloud-studio-repo'
$taskStudy='C:\Users\kaanb\CloudCrushing\sensitivity_20260907'
$taskFrom=Join-Path $taskStudy 'gasoline'
$taskBase='1a105f1e860298f4380d053d390c1a119ecdc5a0'
$taskFiles=@('README.md','DIVERGENCE_REVIEW.md','DIVERGENCE_REVIEW_PLAN.md','review_divergence.py','test_review_divergence.py','divergence_review.json','publish_gasoline_divergence.ps1')
$taskCopies=@()
foreach($taskName in $taskFiles){$taskCopies+=,@((Join-Path $taskFrom $taskName),('analysis/sensitivity_20260907/gasoline/'+$taskName))}
foreach($taskName in @('README.md','PLAN.md')){$taskCopies+=,@((Join-Path $taskStudy $taskName),('analysis/sensitivity_20260907/'+$taskName))}
$taskCopies+=,@((Join-Path $taskStudy 'analysis_index.md'),'analysis/README.md')
$taskStatus=@(git -C $taskRepo status --porcelain)
if($LASTEXITCODE -ne 0 -or $taskStatus.Count){throw 'Review unexpected working-tree changes'}
if($Mode -eq 'stage'){
 if((git -C $taskRepo rev-parse HEAD).Trim() -ne $taskBase){throw 'Unexpected publication base'}
 $taskReportPath=Join-Path $taskFrom 'divergence_review.json'
 if((Get-FileHash -LiteralPath $taskReportPath).Hash.ToLower() -ne '96ee1e31635feae95674bd4777a0d9e5badc288a860112cb86dc40e6ef8957b2'){throw 'Read-only evidence changed'}
 $taskReport=Get-Content -Raw -LiteralPath $taskReportPath | ConvertFrom-Json
 if($taskReport.status -ne 'read_only_divergence_review_complete_scientific_hold_unchanged' -or $taskReport.original_gate_passed -or $taskReport.full_controls_added -ne 0 -or $taskReport.summary.native_checkpoints_decoded -ne 8){throw 'Unexpected read-only result'}
 foreach($taskName in @('review_divergence.py','test_review_divergence.py','DIVERGENCE_REVIEW_PLAN.md')){
  $taskPinned='/home/kaan/sensitivity_20260907/gasoline/read_only_divergence_v1/'+$taskName
  if((Get-FileHash -LiteralPath (Join-Path $taskFrom $taskName)).Hash.ToLower() -ne $taskReport.pins.$taskPinned){throw ('Frozen analysis source changed: '+$taskName)}
 }
 foreach($taskCopy in $taskCopies){
  $taskTarget=[IO.Path]::GetFullPath((Join-Path $taskRepo $taskCopy[1]))
  if(!$taskTarget.StartsWith($taskRepo+'\analysis\',[StringComparison]::OrdinalIgnoreCase)){throw 'Outside analysis'}
  $taskTemp=$taskTarget+'.publish.tmp'
  if(Test-Path -LiteralPath $taskTemp){throw 'Staging temporary exists'}
  Copy-Item -LiteralPath $taskCopy[0] -Destination $taskTemp
  if((Get-FileHash -LiteralPath $taskCopy[0]).Hash -ne (Get-FileHash -LiteralPath $taskTemp).Hash){throw 'Copy mismatch'}
  Move-Item -LiteralPath $taskTemp -Destination $taskTarget -Force
 }
 Write-Output ('Prepared '+$taskCopies.Count+' custom analysis files. No simulations or viewer entries added.');exit
}
$taskProofPath=Join-Path $taskFrom 'divergence_publication.json'
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
$taskProof=[ordered]@{status='verified_live';verified_at_utc=[DateTime]::UtcNow.ToString('o');commit=$Commit;previous_commit=$taskBase;pages_workflow_id=$WorkflowId;files_verified=$taskChecks.Count;checks=$taskChecks;scope='Read-only Gasoline divergence review. Native double differences verified; original failed gate retained. No new simulations or production viewer entries. Accepted total46.'}
$taskTemp=$taskProofPath+'.tmp';if(Test-Path -LiteralPath $taskTemp){throw 'Proof temporary exists'}
[IO.File]::WriteAllText($taskTemp,($taskProof|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
Move-Item -LiteralPath $taskTemp -Destination $taskProofPath
[pscustomobject]$taskProof | Select-Object status,verified_at_utc,commit,pages_workflow_id,files_verified | ConvertTo-Json -Compress
