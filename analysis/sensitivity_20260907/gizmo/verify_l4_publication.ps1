$ErrorActionPreference='Stop'
$taskRepo='C:\Users\kaanb\cloud-studio-repo'
$taskOutput='C:\Users\kaanb\CloudCrushing\sensitivity_20260907\gizmo\l4_publication.json'
$taskCommit='c58b730164e6ab193d075eb9c42d20d4d787cea6'
$taskPrevious='5d222423e8d94e5ad6e76dc7c7e1f6b017505031'
if(Test-Path -LiteralPath $taskOutput){throw 'Completed publication proof already exists; preserve it'}
$taskHead=(git -C $taskRepo rev-parse HEAD).Trim()
$taskRemote=(git -C $taskRepo ls-remote origin refs/heads/main).Split()[0]
if($taskHead -ne $taskCommit -or $taskRemote -ne $taskCommit -or $taskHead -eq $taskPrevious){throw 'Local/remote publication commit not advanced and equal'}
if(@(git -C $taskRepo status --porcelain).Count){throw 'Unexpected repository changes'}
$taskRun=Invoke-RestMethod 'https://api.github.com/repos/KaanBoge/cloud-studio/actions/runs/34188583805' -Headers @{'User-Agent'='CloudStudio-verification'}
if($taskRun.status -ne 'completed'){Write-Output ('Pages still '+$taskRun.status);exit 2}
if($taskRun.conclusion -ne 'success' -or $taskRun.head_sha -ne $taskCommit){throw 'Pages did not deploy the expected commit successfully'}
Add-Type -AssemblyName System.Net.Http
$taskClient=[System.Net.Http.HttpClient]::new()
$taskClient.DefaultRequestHeaders.UserAgent.ParseAdd('CloudStudio-verification/1.0')
$taskClient.Timeout=[TimeSpan]::FromSeconds(30)
$taskFiles=@(git -C $taskRepo diff-tree --no-commit-id --name-only -r $taskCommit)
$taskChecks=@()
try{
  foreach($taskFile in $taskFiles){
    if(!$taskFile.StartsWith('analysis/')){throw 'Unexpected file outside analysis publication'}
    $taskUrl='https://kaanboge.github.io/cloud-studio/'+$taskFile+'?v='+$taskCommit
    $taskResponse=$taskClient.GetAsync($taskUrl).GetAwaiter().GetResult()
    $taskResponse.EnsureSuccessStatusCode() | Out-Null
    $taskBytes=$taskResponse.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult()
    $taskHasher=[System.Security.Cryptography.SHA256]::Create()
    try{$taskHash=([BitConverter]::ToString($taskHasher.ComputeHash($taskBytes))).Replace('-','').ToLower()}finally{$taskHasher.Dispose()}
    $taskLocalHash=(Get-FileHash -LiteralPath (Join-Path $taskRepo $taskFile)).Hash.ToLower()
    if($taskHash -ne $taskLocalHash){throw "Live bytes differ: $taskFile"}
    $taskChecks+=[ordered]@{path=$taskFile;url=$taskUrl;status=[int]$taskResponse.StatusCode;bytes=$taskBytes.Length;sha256=$taskHash}
    $taskResponse.Dispose()
  }
}finally{$taskClient.Dispose()}
if($taskChecks.Count -ne 13){throw 'Unexpected publication file count'}
$taskProof=[ordered]@{status='verified_live';verified_at_utc=[DateTime]::UtcNow.ToString('o');commit=$taskCommit;previous_commit=$taskPrevious;remote_main_matches=$true;working_tree_clean=$true;pages_workflow_id=$taskRun.id;pages_conclusion=$taskRun.conclusion;files_verified=$taskChecks.Count;checks=$taskChecks;scope='Native MFM L4 setup/timing validation,16 independent native test states,9 additional unit tests and the frozen guarded full-pair launcher. Full pair launched but not yet completed/accepted. Total accepted and analyzed controls remains40. No native raw, binaries or new production viewer entries published.'}
$taskTemp=$taskOutput+'.tmp'
if(Test-Path -LiteralPath $taskTemp){throw 'Unexpected proof temporary file'}
[IO.File]::WriteAllText($taskTemp,($taskProof|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
Move-Item -LiteralPath $taskTemp -Destination $taskOutput
[pscustomobject]$taskProof | Select-Object status,verified_at_utc,commit,pages_workflow_id,pages_conclusion,files_verified,scope | ConvertTo-Json -Depth 3
