param([ValidateSet('stage','verify')][string]$Mode='stage',[string]$Commit,[long]$WorkflowId)
$ErrorActionPreference='Stop'
$taskRepo='C:\Users\kaanb\cloud-studio-repo'
$taskStudy='C:\Users\kaanb\CloudCrushing\sensitivity_20260907'
$taskFrom=Join-Path $taskStudy 'gasoline'
$taskBase='fab87c1f0f152feaf6533f93b9a74ebd02e495db'
$taskFiles=@('README.md','SERIAL_OBSERVER_VALIDATION.md','SERIAL_OBSERVER_PLAN.md','SERIAL_OBSERVER_PLAN_V2.md','serial_observer_run_v2.py','test_serial_observer_run_v2.py','serial_observer_v2.h','test_serial_observer_v2.c','serial_observer_plan_v2.json','serial_observer_result_v2.json','serial_observer_v1_failure.json','serial_observer_v1_native_result.json','publish_serial_observer.ps1')
$taskCopies=@()
foreach($taskName in $taskFiles){$taskCopies+=,@((Join-Path $taskFrom $taskName),('analysis/sensitivity_20260907/gasoline/'+$taskName))}
foreach($taskName in @('README.md','PLAN.md')){$taskCopies+=,@((Join-Path $taskStudy $taskName),('analysis/sensitivity_20260907/'+$taskName))}
$taskCopies+=,@((Join-Path $taskStudy 'analysis_index.md'),'analysis/README.md')
$taskStatus=@(git -C $taskRepo status --porcelain)
if($LASTEXITCODE -ne 0 -or $taskStatus.Count){throw 'Review unexpected working-tree changes'}
if($Mode -eq 'stage'){
 if((git -C $taskRepo rev-parse HEAD).Trim() -ne $taskBase){throw 'Unexpected publication base'}
 $taskReportPath=Join-Path $taskFrom 'serial_observer_result_v2.json'
 if((Get-FileHash -LiteralPath $taskReportPath).Hash.ToLower() -ne 'bd196f0028d551e22cfbbfe6673c85d8ba29cb51f236719b04dbfd7ba83057af'){throw 'Native observer evidence changed'}
 $taskReport=Get-Content -Raw -LiteralPath $taskReportPath | ConvertFrom-Json
 if($taskReport.status -ne 'passed_observed_serial_particle_bytes_not_trajectory_equivalence' -or !$taskReport.old_field_gate_still_failed -or $taskReport.full_controls_added -ne 0 -or $taskReport.native_states.Count -ne 2 -or $taskReport.checkpoint.header.valid -ne 1 -or $taskReport.observer_records.Count -ne 3 -or @($taskReport.observer_records | Where-Object {!$_.equal}).Count){throw 'Unexpected native observer result'}
 $taskPlanPath=Join-Path $taskFrom 'serial_observer_plan_v2.json'
 if((Get-FileHash -LiteralPath $taskPlanPath).Hash.ToLower() -ne '5c383a4772b36252bf8edf79ef66affea3a4e67b74973df66146d416c07d9c79'){throw 'Frozen native observer plan changed'}
 $taskPlan=Get-Content -LiteralPath $taskPlanPath -Raw | ConvertFrom-Json
 foreach($taskName in @('serial_observer_run_v2.py','test_serial_observer_run_v2.py','serial_observer_v2.h','test_serial_observer_v2.c','SERIAL_OBSERVER_PLAN.md','SERIAL_OBSERVER_PLAN_V2.md')){
  $taskPinned='/home/kaan/sensitivity_20260907/gasoline/serial_observer_runner_v2/'+$taskName
  if((Get-FileHash -LiteralPath (Join-Path $taskFrom $taskName)).Hash.ToLower() -ne $taskPlan.pins.$taskPinned){throw ('Frozen diagnostic source changed: '+$taskName)}
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
 Write-Output ('Prepared '+$taskCopies.Count+' custom diagnostic files. No full controls or viewer entries added.');exit
}
$taskProofPath=Join-Path $taskFrom 'serial_observer_publication.json'
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
$taskProof=[ordered]@{status='verified_live';verified_at_utc=[DateTime]::UtcNow.ToString('o');commit=$Commit;previous_commit=$taskBase;pages_workflow_id=$WorkflowId;files_verified=$taskChecks.Count;checks=$taskChecks;scope='Gasoline native serial writer preserved observed particle buffers/counts. Two short diagnostic states and checkpoint retained. First failed preparation retained separately. Trajectory hold remains; accepted total46. No new full controls or production viewer entries.'}
$taskTemp=$taskProofPath+'.tmp';if(Test-Path -LiteralPath $taskTemp){throw 'Proof temporary exists'}
[IO.File]::WriteAllText($taskTemp,($taskProof|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
Move-Item -LiteralPath $taskTemp -Destination $taskProofPath
[pscustomobject]$taskProof | Select-Object status,verified_at_utc,commit,pages_workflow_id,files_verified | ConvertTo-Json -Compress
