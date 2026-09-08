param([ValidateSet('stage','verify')][string]$Mode='stage',[string]$Commit,[long]$WorkflowId)
$ErrorActionPreference='Stop'
$taskRepo='C:\Users\kaanb\cloud-studio-repo'
$taskStudy='C:\Users\kaanb\CloudCrushing\sensitivity_20260907'
$taskBase='584d80e1bd55b9ac8143311729d71e189341347b'
$taskFiles=@('README.md','PLAN.md','gadget4/README.md','gadget4/analyze_levels_v1.py','gadget4/test_levels_v1.py',
 'gadget4/run_l4_direct_storage.py','gadget4/test_l4_direct_storage.py','gadget4/prepare_l4_direct_storage.py',
 'gadget4/launch_l4_direct_storage.ps1','gadget4/L4_DIRECT_STORAGE_PLAN.md','gadget4/publish_levels_v1.ps1',
 'gadget4/analysis_levels_v1/README.md','gadget4/analysis_levels_v1/report.json',
 'gadget4/analysis_levels_v1/validation.json','gadget4/analysis_levels_v1/mass_L3_L4.png',
 'gadget4/analysis_levels_v1/full_l4_batch.json','gadget4/analysis_levels_v1/full_l4_plan.json',
 'gadget4/analysis_levels_v1/windows_readback.json')
$taskCopies=@()
foreach($taskName in $taskFiles){$taskCopies+=,@((Join-Path $taskStudy $taskName),('analysis/sensitivity_20260907/'+$taskName))}
$taskCopies+=,@((Join-Path $taskStudy 'analysis_index.md'),'analysis/README.md')
if(@(git -C $taskRepo status --porcelain).Count){throw 'Unexpected repository changes'}
$taskReport=Get-Content -Raw -LiteralPath (Join-Path $taskStudy 'gadget4/analysis_levels_v1/report.json') | ConvertFrom-Json
$taskValidation=Get-Content -Raw -LiteralPath (Join-Path $taskStudy 'gadget4/analysis_levels_v1/validation.json') | ConvertFrom-Json
if($taskReport.status -ne 'share_with_caveats' -or $taskReport.controls -ne 4 -or $taskReport.native_states -ne 404 -or $taskReport.new_controls -ne 2 -or $taskValidation.unit_tests_passed -ne 12 -or $taskValidation.new_snapshots_byte_verified -ne 202 -or $taskValidation.new_restart_files_byte_verified -ne 16 -or $taskValidation.native_experiments_rerun -ne 0){throw 'Unexpected validated scope'}
foreach($taskCheck in @(
 @('gadget4/analysis_levels_v1/report.json',$taskValidation.report_sha256),
 @('gadget4/analysis_levels_v1/mass_L3_L4.png',$taskReport.plot_sha256),
 @('gadget4/analyze_levels_v1.py',$taskReport.analysis_sha256),
 @('gadget4/test_levels_v1.py',$taskValidation.test_script_sha256),
 @('gadget4/analysis_levels_v1/full_l4_plan.json','a66c291cdaf6858a0c69560a47ed137f5d026e85851af205134b5cb0d67bdba4')
)){
 if((Get-FileHash -LiteralPath (Join-Path $taskStudy $taskCheck[0])).Hash.ToLower() -ne $taskCheck[1]){throw ('Changed validated source: '+$taskCheck[0])}
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
   if(!(Test-Path -LiteralPath (Join-Path (Split-Path -Parent (Join-Path $taskRepo $taskCopy[1])) ($taskLink -split '#',2)[0]))){throw ('Missing relative link: '+$taskLink)}
   $taskLinks++
  }
 }
 $taskPaths=@($taskCopies | ForEach-Object {$_[1]})
 git -C $taskRepo -c core.autocrlf=false add -- $taskPaths
 if($LASTEXITCODE -ne 0){throw 'Git add failed'}
 foreach($taskCopy in $taskCopies){
  if((git -C $taskRepo hash-object --no-filters $taskCopy[0]).Trim() -ne (git -C $taskRepo rev-parse (':'+$taskCopy[1])).Trim()){throw 'Staged bytes changed'}
 }
 git -C $taskRepo -c core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol diff --cached --check
 if($LASTEXITCODE -ne 0){throw 'Staged whitespace check failed'}
 $taskChanged=@(git -C $taskRepo diff --cached --name-only)
 if(@(Compare-Object $taskChanged $taskPaths).Count){throw 'Unexpected staged scope'}
 Write-Output ('Staged '+$taskCopies.Count+' validated analysis files; checked '+$taskLinks+' relative links. No production viewer/native artifacts.');exit
}
$taskProofPath=Join-Path $taskStudy 'gadget4/analysis_levels_v1/publication.json'
if(Test-Path -LiteralPath $taskProofPath){throw 'Completed proof exists'}
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
$taskProof=[ordered]@{status='verified_live';verified_at_utc=[DateTime]::UtcNow.ToString('o');commit=$Commit;previous_commit=$taskBase;pages_workflow_id=$WorkflowId;files_verified=$taskChecks.Count;checks=$taskChecks;scope='Gadget-4 L3/L4 comparison: four accepted controls,404 native states,two new L4 controls. Study total48controls/4852states. No old rerun,raw deletion or new production viewer entry.'}
$taskTemp=$taskProofPath+'.tmp';if(Test-Path -LiteralPath $taskTemp){throw 'Proof temporary exists'}
[IO.File]::WriteAllText($taskTemp,($taskProof|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
Move-Item -LiteralPath $taskTemp -Destination $taskProofPath
[pscustomobject]$taskProof | Select-Object status,verified_at_utc,commit,pages_workflow_id,files_verified | ConvertTo-Json -Compress
