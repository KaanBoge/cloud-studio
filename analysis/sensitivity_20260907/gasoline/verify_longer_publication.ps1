param([Parameter(Mandatory=$true)][string]$ExpectedCommit,[Parameter(Mandatory=$true)][long]$WorkflowId)
$ErrorActionPreference='Stop'
$taskRepo='C:\Users\kaanb\cloud-studio-repo'
$taskOutput=Join-Path $PSScriptRoot 'longer_publication.json'
$taskPrevious='8964a45421318f7759ab81570a8b2f214cc0781f'
if(Test-Path -LiteralPath $taskOutput){throw 'Completed proof exists; do not overwrite'}
if($ExpectedCommit -notmatch '^[0-9a-f]{40}$'){throw 'Expected full commit hash'}
$taskHead=(git -C $taskRepo rev-parse HEAD).Trim()
$taskRemote=(git -C $taskRepo ls-remote origin refs/heads/main).Split()[0]
if($taskHead -ne $ExpectedCommit -or $taskRemote -ne $ExpectedCommit -or $taskHead -eq $taskPrevious){throw 'Expected advanced matching local/remote commit'}
if(@(git -C $taskRepo status --porcelain).Count){throw 'Unexpected repository changes'}
$taskRun=Invoke-RestMethod ('https://api.github.com/repos/KaanBoge/cloud-studio/actions/runs/'+$WorkflowId) -Headers @{'User-Agent'='CloudStudio-verification'}
if($taskRun.status -ne 'completed'){Write-Output ('Pages still '+$taskRun.status);exit 2}
if($taskRun.conclusion -ne 'success' -or $taskRun.head_sha -ne $ExpectedCommit){throw 'Pages did not deploy expected commit'}
Add-Type -AssemblyName System.Net.Http
$taskClient=[System.Net.Http.HttpClient]::new()
$taskClient.DefaultRequestHeaders.UserAgent.ParseAdd('CloudStudio-verification/1.0')
$taskClient.Timeout=[TimeSpan]::FromSeconds(30)
$taskFiles=@(git -C $taskRepo diff-tree --no-commit-id --name-only -r $ExpectedCommit)
$taskChecks=@()
try {
 foreach($taskFile in $taskFiles){
  if(!$taskFile.StartsWith('analysis/')){throw 'Unexpected publication path'}
  $taskSurface='live_pages'
  $taskUrl='https://kaanboge.github.io/cloud-studio/'+$taskFile+'?v='+$ExpectedCommit
  if($taskFile.EndsWith('/.gitattributes')){
   $taskSurface='repository_config'
   $taskUrl='https://raw.githubusercontent.com/KaanBoge/cloud-studio/'+$ExpectedCommit+'/'+$taskFile
  }
  $taskResponse=$taskClient.GetAsync($taskUrl).GetAwaiter().GetResult()
  $taskResponse.EnsureSuccessStatusCode() | Out-Null
  $taskBytes=$taskResponse.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult()
  $taskHash=([BitConverter]::ToString([Security.Cryptography.SHA256]::HashData($taskBytes))).Replace('-','').ToLower()
  $taskLocalHash=(Get-FileHash -LiteralPath (Join-Path $taskRepo $taskFile)).Hash.ToLower()
  if($taskHash -ne $taskLocalHash){throw ('Live bytes differ: '+$taskFile)}
  $taskChecks+=[ordered]@{path=$taskFile;surface=$taskSurface;url=$taskUrl;status=[int]$taskResponse.StatusCode;bytes=$taskBytes.Length;sha256=$taskHash}
  $taskResponse.Dispose()
 }
} finally {$taskClient.Dispose()}
if($taskChecks.Count -ne 24){throw 'Unexpected changed-file count'}
$taskProof=[ordered]@{status='verified_live';verified_at_utc=[DateTime]::UtcNow.ToString('o');commit=$ExpectedCommit;previous_commit=$taskPrevious;remote_main_matches=$true;working_tree_clean=$true;pages_workflow_id=$WorkflowId;pages_conclusion=$taskRun.conclusion;files_verified=@($taskChecks | Where-Object {$_.surface -eq 'live_pages'}).Count;repository_config_files_verified=1;checks=$taskChecks;scope='Gasoline81-state prospective failure audit, exact dense-mass agreement through1tcc, checkpoint retention and whole-pair storage measurements. No full Gasoline controls or production viewer entries. Accepted total44. Native raw and failed attempts retained.'}
$taskTemp=$taskOutput+'.tmp'
if(Test-Path -LiteralPath $taskTemp){throw 'Unexpected proof temporary'}
[IO.File]::WriteAllText($taskTemp,($taskProof|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
Move-Item -LiteralPath $taskTemp -Destination $taskOutput
[pscustomobject]$taskProof | Select-Object status,verified_at_utc,commit,pages_workflow_id,files_verified | ConvertTo-Json -Compress
