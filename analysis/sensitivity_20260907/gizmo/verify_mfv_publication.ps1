param([Parameter(Mandatory=$true)][string]$ExpectedCommit,[Parameter(Mandatory=$true)][long]$WorkflowId)
$ErrorActionPreference='Stop'
$taskRepo='C:\Users\kaanb\cloud-studio-repo'
$taskOutput=Join-Path $PSScriptRoot 'mfv_restart_publication.json'
$taskBase='ceffdc9ad3d7f6432054de541e7224c3235f51a1'
if(Test-Path -LiteralPath $taskOutput){throw 'Completed proof exists; do not overwrite'}
if($ExpectedCommit -notmatch '^[0-9a-f]{40}$'){throw 'Expected full commit hash'}
if((git -C $taskRepo rev-parse HEAD).Trim() -ne $ExpectedCommit -or (git -C $taskRepo ls-remote origin refs/heads/main).Split()[0] -ne $ExpectedCommit -or $ExpectedCommit -eq $taskBase){throw 'Expected advanced matching local/remote commit'}
if(@(git -C $taskRepo status --porcelain).Count){throw 'Unexpected repo changes'}
$taskRun=Invoke-RestMethod ('https://api.github.com/repos/KaanBoge/cloud-studio/actions/runs/'+$WorkflowId) -Headers @{'User-Agent'='CloudStudio-verification'}
if($taskRun.status -ne 'completed'){Write-Output ('Pages still '+$taskRun.status);exit 2}
if($taskRun.conclusion -ne 'success' -or $taskRun.head_sha -ne $ExpectedCommit){throw 'Pages did not deploy expected commit'}
Add-Type -AssemblyName System.Net.Http
$taskClient=[System.Net.Http.HttpClient]::new()
$taskClient.DefaultRequestHeaders.UserAgent.ParseAdd('CloudStudio-verification/1.0')
$taskClient.Timeout=[TimeSpan]::FromSeconds(30)
$taskFiles=@(git -C $taskRepo diff-tree --no-commit-id --name-only -r $ExpectedCommit)
if($taskFiles.Count -ne 14){throw 'Unexpected changed-file count'}
$taskChecks=@()
try {
 foreach($taskFile in $taskFiles){
  if(!$taskFile.StartsWith('analysis/')){throw 'Unexpected publication scope'}
  $taskSurface='live_pages'
  $taskUrl='https://kaanboge.github.io/cloud-studio/'+$taskFile+'?v='+$ExpectedCommit
  if($taskFile.EndsWith('/.gitattributes')){
   $taskSurface='repository_config'
   $taskUrl='https://raw.githubusercontent.com/KaanBoge/cloud-studio/'+$ExpectedCommit+'/'+$taskFile
  }
  $taskResponse=$taskClient.GetAsync($taskUrl).GetAwaiter().GetResult()
  try {
   $taskResponse.EnsureSuccessStatusCode() | Out-Null
   $taskBytes=$taskResponse.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult()
   $taskHash=([BitConverter]::ToString([Security.Cryptography.SHA256]::HashData($taskBytes))).Replace('-','').ToLower()
   if($taskHash -ne (Get-FileHash -LiteralPath (Join-Path $taskRepo $taskFile)).Hash.ToLower()){throw ('Live bytes differ: '+$taskFile)}
   $taskChecks+=[ordered]@{path=$taskFile;surface=$taskSurface;url=$taskUrl;status=[int]$taskResponse.StatusCode;bytes=$taskBytes.Length;sha256=$taskHash}
  } finally {$taskResponse.Dispose()}
 }
} finally {$taskClient.Dispose()}
$taskProof=[ordered]@{status='verified_live';verified_at_utc=[DateTime]::UtcNow.ToString('o');commit=$ExpectedCommit;previous_commit=$taskBase;remote_main_matches=$true;working_tree_clean=$true;pages_workflow_id=$WorkflowId;pages_conclusion=$taskRun.conclusion;files_verified=@($taskChecks | Where-Object {$_.surface -eq 'live_pages'}).Count;checks=$taskChecks;scope='MFV terminal restart/export diagnosis only;44 accepted full controls unchanged. All raw states retained. No new simulation, compiler/floor change or production viewer entry.'}
$taskTemp=$taskOutput+'.tmp'
if(Test-Path -LiteralPath $taskTemp){throw 'Existing proof temporary'}
[IO.File]::WriteAllText($taskTemp,($taskProof|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
Move-Item -LiteralPath $taskTemp -Destination $taskOutput
[pscustomobject]$taskProof | Select-Object status,verified_at_utc,commit,pages_workflow_id,files_verified | ConvertTo-Json -Compress
