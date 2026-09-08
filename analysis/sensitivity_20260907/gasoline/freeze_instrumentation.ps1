$ErrorActionPreference='Stop'
$taskRoot='\\wsl.localhost\Ubuntu\home\kaan\sensitivity_20260907\gasoline'
$taskBundle=Join-Path $taskRoot 'runner_instrumentation_v1'
if(Test-Path -LiteralPath $taskBundle){throw 'Existing frozen bundle'}
$taskOriginal=Get-Content -Raw -LiteralPath (Join-Path $taskRoot 'copy_manifest.json') | ConvertFrom-Json
$taskChanged=@()
foreach($taskFile in $taskOriginal.files){
  if((Get-FileHash -LiteralPath $taskFile.source).Hash.ToLower() -ne $taskFile.sha256){throw 'Canonical source changed during isolated preparation'}
  if((Get-FileHash -LiteralPath $taskFile.copy).Hash.ToLower() -ne $taskFile.sha256){$taskChanged+=$taskFile.copy}
}
if($taskChanged.Count -ne 3){throw 'Unexpected number of isolated build changes'}
foreach($taskFile in $taskChanged){
  if((Split-Path -Leaf $taskFile) -notin @('main.c','main.o','gasoline')){throw 'Unexpected native build change'}
}
New-Item -ItemType Directory -Path $taskBundle | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'gasoline_controls.py'),(Join-Path $PSScriptRoot 'test_gasoline.py') -Destination $taskBundle
& wsl.exe --exec env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /home/kaan/venv/bin/python /home/kaan/sensitivity_20260907/gasoline/runner_instrumentation_v1/test_gasoline.py
if($LASTEXITCODE -ne 0){throw 'Frozen tests failed'}
$taskPins=[ordered]@{}
$taskPaths=@((Join-Path $taskBundle 'gasoline_controls.py'),(Join-Path $taskBundle 'test_gasoline.py'),(Join-Path $taskRoot 'instrumentation_v1\preparation.json'),(Join-Path $taskRoot 'gasoline_original'))
$taskPaths+=@($taskOriginal.files | ForEach-Object {$_.copy})
foreach($taskPath in $taskPaths){
  $taskLinux=$taskPath.Substring('\\wsl.localhost\Ubuntu'.Length).Replace('\','/')
  $taskPins[$taskLinux]=(Get-FileHash -LiteralPath $taskPath).Hash.ToLower()
}
$taskReport=[ordered]@{status='tested_frozen_instrumentation_only';tests_passed=7;created=(Get-Date).ToString('o');native_changed_files=$taskChanged;pinned_files=$taskPins;full_science_controls_completed=0}
$taskJson=$taskReport | ConvertTo-Json -Depth 8
[IO.File]::WriteAllText((Join-Path $taskBundle 'bundle.json'),$taskJson)
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'instrumentation_bundle.json'),$taskJson)
[pscustomobject]@{status=$taskReport.status;tests_passed=7;changed_files=$taskChanged;bundle_sha256=(Get-FileHash -LiteralPath (Join-Path $taskBundle 'bundle.json')).Hash.ToLower()}
