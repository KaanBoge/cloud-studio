param([ValidateSet('stage','verify')][string]$Mode='stage',[string]$Commit,[long]$WorkflowId)
$ErrorActionPreference='Stop'
$taskRepo='C:\Users\kaanb\cloud-studio-repo'
$taskStudy='C:\Users\kaanb\CloudCrushing\sensitivity_20260907'
$taskFrom=Join-Path $taskStudy 'gasoline'
$taskBase='492f2f186a65b0ab1067b9f730336fb651ec9b55'
$taskFiles=@('README.md','FORCE_ORDER_RESULTS.md','FORCE_ORDER_TRACE_DESIGN.md','FORCE_TRACE_CORE_VALIDATION.md','FORCE_COMPARISON_PLAN.md','force_trace_core.h','test_force_trace_core.c','force_trace_replay.py','test_force_trace_replay.py','prepare_force_trace_core.py','force_trace_core_plan.json','force_trace_core_report.json','force_trace_native.h','test_force_trace_native.c','prepare_force_native.py','run_force_order.py','test_run_force_order.py','compare_force_order.py','test_compare_force_order.py','review_force_comparison.py','force_native_build.json','force_native_plan.json','force_native_report.json','force_comparison_plan.json','force_comparison_report.json','force_comparison_review.json','publish_force_order.ps1')
$taskCopies=@()
foreach($taskName in $taskFiles){$taskCopies+=,@((Join-Path $taskFrom $taskName),('analysis/sensitivity_20260907/gasoline/'+$taskName))}
foreach($taskName in @('README.md','PLAN.md')){$taskCopies+=,@((Join-Path $taskStudy $taskName),('analysis/sensitivity_20260907/'+$taskName))}
$taskCopies+=,@((Join-Path $taskStudy 'analysis_index.md'),'analysis/README.md')
$taskStatus=@(git -C $taskRepo status --porcelain)
if($LASTEXITCODE -ne 0 -or $taskStatus.Count){throw 'Unexpected working-tree changes'}
if($Mode -eq 'stage'){
 if((git -C $taskRepo rev-parse HEAD).Trim() -ne $taskBase){throw 'Unexpected publication base'}
 $taskHashes=@{
  'force_native_report.json'='94ed097aa774b930c065bb1710d2c4f4f9d4cf618adcf09c52b23debf8822b97';
  'force_comparison_report.json'='5c78fd85a3f5dc35800443a200955a883ecd97dce512b1bc7af665c48c66f7ef';
  'force_comparison_review.json'='a20b4b4a746a83d701bd528e1958c40eb287321a4c5b988d2d6e8f6c3c1c453b';
  'force_trace_core_report.json'='69100849bf2cd4423d6f91bfcf82e887a87bff62bc1ffa4719ad8118eed772cb'
 }
 foreach($taskName in $taskHashes.Keys){if((Get-FileHash -LiteralPath (Join-Path $taskFrom $taskName)).Hash.ToLower() -ne $taskHashes[$taskName]){throw ('Evidence changed: '+$taskName)}}
 $taskNative=Get-Content -LiteralPath (Join-Path $taskFrom 'force_native_report.json') -Raw | ConvertFrom-Json
 $taskAnalysis=Get-Content -LiteralPath (Join-Path $taskFrom 'force_comparison_report.json') -Raw | ConvertFrom-Json
 $taskReview=Get-Content -LiteralPath (Join-Path $taskFrom 'force_comparison_review.json') -Raw | ConvertFrom-Json
 if($taskNative.native_states_added -ne 4 -or $taskNative.full_controls_added -ne 0 -or !$taskAnalysis.old_field_gate_still_failed -or $taskAnalysis.full_gasoline_controls_enabled -or $taskAnalysis.paired_accumulators -ne 1638 -or $taskReview.order_comparisons_checked -ne 27 -or $taskReview.exact_rational_owner_sums_checked -ne 54){throw 'Unexpected result scope'}
 $taskPinObjects=@()
 $taskCore=Get-Content -LiteralPath (Join-Path $taskFrom 'force_trace_core_plan.json') -Raw | ConvertFrom-Json
 $taskBuild=Get-Content -LiteralPath (Join-Path $taskFrom 'force_native_build.json') -Raw | ConvertFrom-Json
 $taskPlan=Get-Content -LiteralPath (Join-Path $taskFrom 'force_native_plan.json') -Raw | ConvertFrom-Json
 $taskComparePlan=Get-Content -LiteralPath (Join-Path $taskFrom 'force_comparison_plan.json') -Raw | ConvertFrom-Json
 $taskPinObjects+=@($taskCore.pins,$taskBuild.artifacts,$taskPlan.pins,$taskComparePlan.source_pins)
 foreach($taskObject in $taskPinObjects){foreach($taskPin in $taskObject.PSObject.Properties){
  $taskName=($taskPin.Name -split '/')[-1]
  if($taskFiles -contains $taskName -and $taskName -match '\.(py|h|c|md)$'){
   if((Get-FileHash -LiteralPath (Join-Path $taskFrom $taskName)).Hash.ToLower() -ne $taskPin.Value){throw ('Frozen source differs: '+$taskName)}
  }
 }}
 if((Get-FileHash -LiteralPath (Join-Path $taskFrom 'review_force_comparison.py')).Hash.ToLower() -ne $taskReview.source_sha256){throw 'Independent review source differs'}
 foreach($taskCopy in $taskCopies){
  $taskTarget=[IO.Path]::GetFullPath((Join-Path $taskRepo $taskCopy[1]))
  if(!$taskTarget.StartsWith($taskRepo+'\analysis\',[StringComparison]::OrdinalIgnoreCase)){throw 'Outside analysis'}
  $taskTemp=$taskTarget+'.publish.tmp'
  if(Test-Path -LiteralPath $taskTemp){throw 'Staging temporary exists'}
  Copy-Item -LiteralPath $taskCopy[0] -Destination $taskTemp
  if((Get-FileHash -LiteralPath $taskCopy[0]).Hash -ne (Get-FileHash -LiteralPath $taskTemp).Hash){throw 'Copy mismatch'}
  Move-Item -LiteralPath $taskTemp -Destination $taskTarget -Force
 }
 Write-Output ('Prepared '+$taskCopies.Count+' reviewed analysis files; zero new full controls or viewer entries.');exit
}
$taskProofPath=Join-Path $taskFrom 'force_order_publication.json'
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
$taskProof=[ordered]@{status='verified_live';verified_at_utc=[DateTime]::UtcNow.ToString('o');commit=$Commit;previous_commit=$taskBase;pages_workflow_id=$WorkflowId;files_verified=$taskChecks.Count;checks=$taskChecks;scope='Three short native force diagnostics: four states and three checkpoints. All27 selected order-only comparisons independently reproduced. Failed density gate remains;46 full controls, no full Gasoline control or viewer entry added.'}
$taskTemp=$taskProofPath+'.tmp';if(Test-Path -LiteralPath $taskTemp){throw 'Proof temporary exists'}
[IO.File]::WriteAllText($taskTemp,($taskProof|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
Move-Item -LiteralPath $taskTemp -Destination $taskProofPath
[pscustomobject]$taskProof | Select-Object status,verified_at_utc,commit,pages_workflow_id,files_verified | ConvertTo-Json -Compress
