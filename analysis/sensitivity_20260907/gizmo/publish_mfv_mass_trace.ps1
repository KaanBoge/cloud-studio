param([ValidateSet('stage','verify')][string]$Mode='stage',[string]$Commit,[long]$WorkflowId)
$ErrorActionPreference='Stop'
$taskRepo='C:\Users\kaanb\cloud-studio-repo'
$taskStudy='C:\Users\kaanb\CloudCrushing\sensitivity_20260907'
$taskFrom=Join-Path $taskStudy 'gizmo'
$taskBase='42932263fbb4bd7f7228a547a3f9dbc0f1a64e3c'
$taskFiles=@('README.md','.gitattributes','MFV_MASS_UPDATE_DEFECT.md','MFV_TIMESTEP_REPAIR_PLAN.md','trace_mfv_mass_update.py','test_mfv_mass_update.py','mfv_mass_update_trace_v1.json','publish_mfv_mass_trace.ps1')
if(@(git -C $taskRepo status --porcelain).Count){throw 'Review unexpected working-tree changes first'}
if($Mode -eq 'stage'){
 if((git -C $taskRepo rev-parse HEAD).Trim() -ne $taskBase){throw 'Unexpected publication base'}
 $taskData=Join-Path $taskFrom 'mfv_mass_update_trace_v1.json'
 if((Get-FileHash -LiteralPath $taskData).Hash.ToLower() -ne '50fae979a156270af8f60d27f7b054e27f9d21a80d96f6ccca0954443a59cf07'){throw 'Trace changed'}
 $taskTrace=Get-Content -Raw -LiteralPath $taskData | ConvertFrom-Json
 if($taskTrace.status -ne 'source_defect_confirmed_causal_repair_test_pending' -or $taskTrace.accepted_full_controls -ne 44 -or $taskTrace.native_simulations_started -ne 0){throw 'Wrong trace status'}
 if((Get-FileHash -LiteralPath (Join-Path $taskFrom 'trace_mfv_mass_update.py')).Hash.ToLower() -ne $taskTrace.script_sha256){throw 'Checker source differs'}
 $taskCopies=@()
 foreach($taskFile in $taskFiles){$taskCopies+=,@((Join-Path $taskFrom $taskFile),('analysis/sensitivity_20260907/gizmo/'+$taskFile))}
 foreach($taskFile in @('README.md','PLAN.md')){$taskCopies+=,@((Join-Path $taskStudy $taskFile),('analysis/sensitivity_20260907/'+$taskFile))}
 $taskCopies+=,@((Join-Path $taskStudy 'analysis_index.md'),'analysis/README.md')
 foreach($taskCopy in $taskCopies){
  $taskTarget=[IO.Path]::GetFullPath((Join-Path $taskRepo $taskCopy[1]))
  if(!$taskTarget.StartsWith($taskRepo+'\analysis\',[StringComparison]::OrdinalIgnoreCase)){throw 'Outside analysis'}
  $taskTemp=$taskTarget+'.publish.tmp'
  if(Test-Path -LiteralPath $taskTemp){throw 'Existing staging temporary'}
  Copy-Item -LiteralPath $taskCopy[0] -Destination $taskTemp
  if((Get-FileHash -LiteralPath $taskCopy[0]).Hash -ne (Get-FileHash -LiteralPath $taskTemp).Hash){throw 'Copy differs'}
  Move-Item -LiteralPath $taskTemp -Destination $taskTarget -Force
 }
 'Staged11 custom analysis files only; no repaired solver or science run.'
 exit
}
$taskProofPath=Join-Path $taskFrom 'mfv_mass_trace_publication.json'
if(Test-Path -LiteralPath $taskProofPath){throw 'Completed publication proof exists'}
if($Commit -notmatch '^[0-9a-f]{40}$' -or $Commit -eq $taskBase -or (git -C $taskRepo rev-parse HEAD).Trim() -ne $Commit -or (git -C $taskRepo ls-remote origin refs/heads/main).Split()[0] -ne $Commit){throw 'Expected advanced matching commit'}
$taskRun=Invoke-RestMethod ('https://api.github.com/repos/KaanBoge/cloud-studio/actions/runs/'+$WorkflowId) -Headers @{'User-Agent'='CloudStudio-verification'}
if($taskRun.status -ne 'completed'){Write-Output ('Pages still '+$taskRun.status);exit 2}
if($taskRun.conclusion -ne 'success' -or $taskRun.head_sha -ne $Commit){throw 'Wrong Pages deployment'}
$taskChanged=@(git -C $taskRepo diff-tree --no-commit-id --name-only -r $Commit)
if($taskChanged.Count -ne 11){throw 'Unexpected publication file count'}
Add-Type -AssemblyName System.Net.Http
$taskClient=[Net.Http.HttpClient]::new()
$taskClient.Timeout=[TimeSpan]::FromSeconds(30)
$taskChecks=@()
try{foreach($taskFile in $taskChanged){
 if(!$taskFile.StartsWith('analysis/')){throw 'Unexpected publication path'}
 $taskSurface='live_pages'
 $taskUrl='https://kaanboge.github.io/cloud-studio/'+$taskFile+'?v='+$Commit
 if($taskFile.EndsWith('/.gitattributes')){$taskSurface='repository_config';$taskUrl='https://raw.githubusercontent.com/KaanBoge/cloud-studio/'+$Commit+'/'+$taskFile}
 $taskBytes=$taskClient.GetByteArrayAsync($taskUrl).GetAwaiter().GetResult()
 $taskHash=([BitConverter]::ToString([Security.Cryptography.SHA256]::HashData($taskBytes))).Replace('-','').ToLower()
 if($taskHash -ne (Get-FileHash -LiteralPath (Join-Path $taskRepo $taskFile)).Hash.ToLower()){throw ('Live bytes differ: '+$taskFile)}
 $taskChecks+=[ordered]@{path=$taskFile;surface=$taskSurface;url=$taskUrl;bytes=$taskBytes.Length;sha256=$taskHash}
}}finally{$taskClient.Dispose()}
$taskProof=[ordered]@{status='verified_live';verified_at_utc=[DateTime]::UtcNow.ToString('o');commit=$Commit;previous_commit=$taskBase;pages_workflow_id=$WorkflowId;pages_conclusion=$taskRun.conclusion;files_verified=@($taskChecks | Where-Object {$_.surface -eq 'live_pages'}).Count;checks=$taskChecks;scope='Native MFV timestep-defect evidence and prospective isolated repair plan; no repaired solver, new run, deletion or accepted-count change.'}
$taskTemp=$taskProofPath+'.tmp'
if(Test-Path -LiteralPath $taskTemp){throw 'Existing proof temporary'}
[IO.File]::WriteAllText($taskTemp,($taskProof|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
Move-Item -LiteralPath $taskTemp -Destination $taskProofPath
[pscustomobject]$taskProof | Select-Object status,verified_at_utc,commit,pages_workflow_id,files_verified | ConvertTo-Json -Compress
