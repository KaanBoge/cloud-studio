param([ValidateSet('stage','verify')][string]$Mode='stage',[string]$Commit,[long]$WorkflowId)
$ErrorActionPreference='Stop'
$taskRepo='C:\Users\kaanb\cloud-studio-repo'
$taskStudy='C:\Users\kaanb\CloudCrushing\sensitivity_20260907'
$taskFrom=Join-Path $taskStudy 'gizmo'
$taskBase='ffe243e51cf961bda40851ddcbae0504d2beadc5'
$taskFiles=@('README.md','.gitattributes','MFV_REPAIR_BUILD_VALIDATION.md','prepare_mfv_repair.ps1','build_mfv_repair.py','test_native_mfv_flux.py','review_mfv_repair_build.py','repair_build_report.json','repair_flux_test_report.json','repair_build_review.json','publish_mfv_repair_build.ps1')
if(@(git -C $taskRepo status --porcelain).Count){throw 'Review unexpected working-tree changes first'}
if($Mode -eq 'stage'){
 if((git -C $taskRepo rev-parse HEAD).Trim() -ne $taskBase){throw 'Unexpected publication base'}
 $taskExpected=@{'repair_build_report.json'='01457ba7a87dfc4054366d240b66f0ba8caca310af74f945eeafb6ebd928e509';'repair_flux_test_report.json'='ffa2d510b2e2737b66bed38ffd03b445694d1f04c3526dd98e0b1f4bd826d340';'repair_build_review.json'='7ac8f279308221ad7a012d33f0e229417d10c38b8aaea42426c3a6eb5950e571'}
 foreach($taskName in $taskExpected.Keys){if((Get-FileHash -LiteralPath (Join-Path $taskFrom $taskName)).Hash.ToLower() -ne $taskExpected[$taskName]){throw 'Changed build evidence'}}
 $taskTests=Get-Content -Raw -LiteralPath (Join-Path $taskFrom 'repair_flux_test_report.json') | ConvertFrom-Json
 if($taskTests.tests -ne 9 -or $taskTests.failures -ne 0 -or $taskTests.errors -ne 0 -or $taskTests.native_simulations_started -ne 0){throw 'Wrong test status'}
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
 'Staged14 custom analysis files only; no native source/binary/raw or science run.'
 exit
}
$taskProofPath=Join-Path $taskFrom 'repair_build_publication.json'
if(Test-Path -LiteralPath $taskProofPath){throw 'Completed publication proof exists'}
if($Commit -notmatch '^[0-9a-f]{40}$' -or $Commit -eq $taskBase -or (git -C $taskRepo rev-parse HEAD).Trim() -ne $Commit -or (git -C $taskRepo ls-remote origin refs/heads/main).Split()[0] -ne $Commit){throw 'Expected advanced matching commit'}
$taskRun=Invoke-RestMethod ('https://api.github.com/repos/KaanBoge/cloud-studio/actions/runs/'+$WorkflowId) -Headers @{'User-Agent'='CloudStudio-verification'}
if($taskRun.status -ne 'completed'){Write-Output ('Pages still '+$taskRun.status);exit 2}
if($taskRun.conclusion -ne 'success' -or $taskRun.head_sha -ne $Commit){throw 'Wrong Pages deployment'}
$taskChanged=@(git -C $taskRepo diff-tree --no-commit-id --name-only -r $Commit)
if($taskChanged.Count -ne 14){throw 'Unexpected publication file count'}
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
$taskProof=[ordered]@{status='verified_live';verified_at_utc=[DateTime]::UtcNow.ToString('o');commit=$Commit;previous_commit=$taskBase;pages_workflow_id=$WorkflowId;pages_conclusion=$taskRun.conclusion;files_verified=@($taskChecks | Where-Object {$_.surface -eq 'live_pages'}).Count;checks=$taskChecks;scope='Isolated MFV reference/repair builds, nine synthetic tests, selected ABI/toolchain/source review. No native evolution, original data/binary change or accepted-count change.'}
$taskTemp=$taskProofPath+'.tmp'
if(Test-Path -LiteralPath $taskTemp){throw 'Existing proof temporary'}
[IO.File]::WriteAllText($taskTemp,($taskProof|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
Move-Item -LiteralPath $taskTemp -Destination $taskProofPath
[pscustomobject]$taskProof | Select-Object status,verified_at_utc,commit,pages_workflow_id,files_verified | ConvertTo-Json -Compress
