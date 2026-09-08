param([ValidateSet('stage','verify')][string]$Mode='stage',[string]$Commit,[long]$WorkflowId)
$ErrorActionPreference='Stop'
$taskRepo='C:\Users\kaanb\cloud-studio-repo'
$taskStudy='C:\Users\kaanb\CloudCrushing\sensitivity_20260907'
$taskFrom=Join-Path $taskStudy 'gizmo'
$taskBase='2958c63601910de541cb6ebc33a04cd600c90179'
$taskFiles=@('README.md','.gitattributes','MFV_REPAIRED_PAIR_VALIDATION.md','MFV_SHARP_PREPARATION_PLAN.md','MFV_SHARP_FULL_PLAN.md','mfv_sharp_prepare.py','test_mfv_sharp_prepare.py','mfv_sharp_full.py','test_mfv_sharp_full.py','plot_mfv_repaired_pair.py','sharp_prepare_plan.json','sharp_prepare_validation.json','sharp_full_plan.json','sharp_full_result.json','mfv_repaired_pair.json','mass_mfv_repaired_L3.png','mfv_repaired_plot.json','publish_mfv_repaired_pair.ps1')
$taskCopies=@()
foreach($taskName in $taskFiles){$taskCopies+=,@((Join-Path $taskFrom $taskName),('analysis/sensitivity_20260907/gizmo/'+$taskName))}
foreach($taskName in @('README.md','PLAN.md')){$taskCopies+=,@((Join-Path $taskStudy $taskName),('analysis/sensitivity_20260907/'+$taskName))}
$taskCopies+=,@((Join-Path $taskStudy 'analysis_index.md'),'analysis/README.md')
$taskStatus=@(git -C $taskRepo status --porcelain)
if($LASTEXITCODE -ne 0 -or $taskStatus.Count){throw 'Review unexpected working-tree changes'}
if($Mode -eq 'stage'){
 if((git -C $taskRepo rev-parse HEAD).Trim() -ne $taskBase){throw 'Unexpected publication base'}
 foreach($taskPair in @(@('sharp_prepare_plan.json','74c54e9db5785752e3193e3130e5d2a3ae94474262ce6121b24e6564adbbe6e8'),@('sharp_prepare_validation.json','41933e9cee047882a0008fe9505e7790151daa7abcef3c619fc03a4699ba97da'),@('sharp_full_plan.json','a4ef923f8a202224f73d79535eba42bcd3d73e6cfb7e9b9254364d62d30b0155'))){
  if((Get-FileHash -LiteralPath (Join-Path $taskFrom $taskPair[0])).Hash.ToLower() -ne $taskPair[1]){throw 'Prospective plan/preparation evidence changed'}
 }
 foreach($taskPlanName in @('sharp_prepare_plan.json','sharp_full_plan.json')){
  $taskPlan=Get-Content -Raw -LiteralPath (Join-Path $taskFrom $taskPlanName) | ConvertFrom-Json
  foreach($taskProperty in $taskPlan.files.PSObject.Properties){
   if((Get-FileHash -LiteralPath (Join-Path $taskFrom $taskProperty.Name)).Hash.ToLower() -ne $taskProperty.Value){throw ('Frozen source changed: '+$taskProperty.Name)}
  }
 }
 $taskReport=Get-Content -Raw -LiteralPath (Join-Path $taskFrom 'mfv_repaired_pair.json') | ConvertFrom-Json
 if($taskReport.status -ne 'passed_repaired_mfv_L3_pair' -or !$taskReport.historical_reused -or $taskReport.accepted_full_controls_after_this_pair -ne 46 -or !$taskReport.sharp_terminal.mass_account.passes -or $taskReport.sharp_cadence.bits -ne 60){throw 'Pair not validated'}
 if((Get-FileHash -LiteralPath (Join-Path $taskFrom 'mfv_sharp_full.py')).Hash.ToLower() -ne $taskReport.script_sha256){throw 'Pair analyzer changed'}
 $taskPlot=Get-Content -Raw -LiteralPath (Join-Path $taskFrom 'mfv_repaired_plot.json') | ConvertFrom-Json
 if((Get-FileHash -LiteralPath (Join-Path $taskFrom 'mfv_repaired_pair.json')).Hash.ToLower() -ne $taskPlot.report_sha256 -or (Get-FileHash -LiteralPath (Join-Path $taskFrom 'mass_mfv_repaired_L3.png')).Hash.ToLower() -ne $taskPlot.plot_sha256 -or (Get-FileHash -LiteralPath (Join-Path $taskFrom 'plot_mfv_repaired_pair.py')).Hash.ToLower() -ne $taskPlot.script_sha256){throw 'Plot provenance differs'}
 foreach($taskCopy in $taskCopies){
  $taskTarget=[IO.Path]::GetFullPath((Join-Path $taskRepo $taskCopy[1]))
  if(!$taskTarget.StartsWith($taskRepo+'\analysis\',[StringComparison]::OrdinalIgnoreCase)){throw 'Outside analysis'}
  $taskTemp=$taskTarget+'.publish.tmp'
  if(Test-Path -LiteralPath $taskTemp){throw 'Staging temporary exists'}
  Copy-Item -LiteralPath $taskCopy[0] -Destination $taskTemp
  if((Get-FileHash -LiteralPath $taskCopy[0]).Hash -ne (Get-FileHash -LiteralPath $taskTemp).Hash){throw 'Copy mismatch'}
  Move-Item -LiteralPath $taskTemp -Destination $taskTarget -Force
 }
 Write-Output ('Prepared '+$taskCopies.Count+' custom analysis files. Raw retained; no viewer entries changed.');exit
}
$taskProofPath=Join-Path $taskFrom 'mfv_repaired_pair_publication.json'
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
 $taskSurface='live_pages';$taskUrl='https://kaanboge.github.io/cloud-studio/'+$taskFile+'?v='+$Commit
 if($taskFile.EndsWith('/.gitattributes')){$taskSurface='repository_config';$taskUrl='https://raw.githubusercontent.com/KaanBoge/cloud-studio/'+$Commit+'/'+$taskFile}
 $taskBytes=$taskClient.GetByteArrayAsync($taskUrl).GetAwaiter().GetResult()
 $taskHash=([BitConverter]::ToString([Security.Cryptography.SHA256]::HashData($taskBytes))).Replace('-','').ToLower()
 if($taskHash -ne (Get-FileHash -LiteralPath (Join-Path $taskRepo $taskFile)).Hash.ToLower()){throw ('Live mismatch: '+$taskFile)}
 $taskChecks+=[ordered]@{path=$taskFile;surface=$taskSurface;url=$taskUrl;bytes=$taskBytes.Length;sha256=$taskHash}
}}finally{$taskClient.Dispose()}
$taskProof=[ordered]@{status='verified_live';verified_at_utc=[DateTime]::UtcNow.ToString('o');commit=$Commit;previous_commit=$taskBase;pages_workflow_id=$WorkflowId;files_verified=@($taskChecks|Where-Object {$_.surface -eq 'live_pages'}).Count;checks=$taskChecks;scope='Repaired MFV L3 pair validated;101 native frames per law. Historical diagnostic reused, missing sharp case newly run. Accepted total46. Native raw retained; no new production3Dviewer entries.'}
$taskTemp=$taskProofPath+'.tmp';if(Test-Path -LiteralPath $taskTemp){throw 'Proof temporary exists'}
[IO.File]::WriteAllText($taskTemp,($taskProof|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
Move-Item -LiteralPath $taskTemp -Destination $taskProofPath
[pscustomobject]$taskProof | Select-Object status,verified_at_utc,commit,pages_workflow_id,files_verified | ConvertTo-Json -Compress
