$ErrorActionPreference='Stop'
$taskRoot='\\wsl.localhost\Ubuntu\home\kaan\sensitivity_20260907\gasoline'
$taskDest=Join-Path $taskRoot 'runner_longer_2rank_v1'
if(Test-Path -LiteralPath $taskDest){throw 'Existing frozen longer-test runner'}
$taskManifest=Get-Content -Raw -LiteralPath (Join-Path $taskRoot 'retained_copy_manifest.json') | ConvertFrom-Json
$taskChanged=@()
foreach($taskFile in $taskManifest){
 if((Get-FileHash -LiteralPath $taskFile.source).Hash.ToLower() -ne $taskFile.sha256){throw 'Earlier frozen native build was changed'}
 if((Get-FileHash -LiteralPath $taskFile.copy).Hash.ToLower() -ne $taskFile.sha256){$taskChanged+=$taskFile.copy}
}
if($taskChanged.Count -ne 3){throw 'Unexpected native retention build diff'}
foreach($taskPath in $taskChanged){if((Split-Path -Leaf $taskPath) -notin @('master.c','master.o','gasoline')){throw 'Unexpected native modification'}}
New-Item -ItemType Directory -Path $taskDest | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'longer_checks_v2.py'),(Join-Path $PSScriptRoot 'test_longer_checks_v2.py'),(Join-Path $PSScriptRoot 'execution_2rank.py') -Destination $taskDest
& wsl.exe --exec env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /home/kaan/venv/bin/python /home/kaan/sensitivity_20260907/gasoline/runner_longer_2rank_v1/test_longer_checks_v2.py
if($LASTEXITCODE -ne 0){throw 'Frozen prospective-check regressions failed'}
$taskPins=[ordered]@{}
$taskPrior=Get-Content -Raw -LiteralPath (Join-Path $taskRoot 'runner_instrumentation_v1\bundle.json') | ConvertFrom-Json
foreach($taskField in $taskPrior.pinned_files.PSObject.Properties){$taskPins[$taskField.Name]=$taskField.Value}
$taskFiles=@((Join-Path $taskDest 'longer_checks_v2.py'),(Join-Path $taskDest 'test_longer_checks_v2.py'),(Join-Path $taskDest 'execution_2rank.py'),(Join-Path $taskRoot 'LONGER_VALIDATION_PLAN.md'),(Join-Path $taskRoot 'LONGER_VALIDATION_PLAN_2RANK.md'),(Join-Path $taskRoot 'longer_validation_2rank_v1\preparation.json'),(Join-Path $taskRoot 'checkpoint_probe.c'),(Join-Path $taskRoot 'checkpoint_probe'))
$taskFiles+=@($taskManifest | ForEach-Object {$_.copy})
foreach($taskFile in $taskFiles){$taskPins[$taskFile.Substring('\\wsl.localhost\Ubuntu'.Length).Replace('\','/')]=(Get-FileHash -LiteralPath $taskFile).Hash.ToLower()}
foreach($taskField in $taskPins.GetEnumerator()){
 $taskPath='\\wsl.localhost\Ubuntu'+$taskField.Key.Replace('/','\')
 if((Get-FileHash -LiteralPath $taskPath).Hash.ToLower() -ne $taskField.Value){throw 'Pinned dependency changed'}
}
$taskReport=[ordered]@{status='frozen_prospective_120_step_2rank_diagnostics';tests_passed=6;earlier_frozen_tests=7;created=(Get-Date).ToString('o');pinned_files=$taskPins;native_retention_changes=$taskChanged;full_science_controls_completed=0}
$taskJson=$taskReport | ConvertTo-Json -Depth 8
[IO.File]::WriteAllText((Join-Path $taskDest 'bundle.json'),$taskJson)
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'longer_2rank_bundle.json'),$taskJson)
[pscustomobject]@{status=$taskReport.status;tests_passed=6;bundle_sha256=(Get-FileHash -LiteralPath (Join-Path $taskDest 'bundle.json')).Hash.ToLower()}
