$ErrorActionPreference='Stop'
$taskRoot='\\wsl.localhost\Ubuntu\home\kaan\sensitivity_20260907\gasoline'
$taskRecord=Join-Path $PSScriptRoot 'longer_2rank_worker_windows.json'
if(Test-Path -LiteralPath $taskRecord){throw 'Existing launch record; verify processes instead of relaunching'}
$taskBundle=Get-Content -Raw -LiteralPath (Join-Path $taskRoot 'runner_longer_2rank_v1\bundle.json') | ConvertFrom-Json
if($taskBundle.status -ne 'frozen_prospective_120_step_2rank_diagnostics'){throw 'Unreviewed runner'}
foreach($taskFile in $taskBundle.pinned_files.PSObject.Properties){
 $taskPath='\\wsl.localhost\Ubuntu'+$taskFile.Name.Replace('/','\')
 if((Get-FileHash -LiteralPath $taskPath).Hash.ToLower() -ne $taskFile.Value){throw 'Pinned file changed'}
}
foreach($taskName in @('original_a','original_b','retained_off','retained_on')){
 if(Test-Path -LiteralPath (Join-Path $taskRoot ('longer_validation_2rank_v1\'+$taskName+'\run_started.json'))){throw 'Existing native run; cannot relaunch'}
}
$taskWorker=Start-Process -FilePath 'wsl.exe' -ArgumentList @('-d','Ubuntu','--exec','env','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1','/home/kaan/venv/bin/python','/home/kaan/sensitivity_20260907/gasoline/runner_longer_2rank_v1/longer_checks_v2.py','run') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $PSScriptRoot 'longer_2rank_worker.log') -RedirectStandardError (Join-Path $PSScriptRoot 'longer_2rank_worker.err.log')
$taskReport=[pscustomobject]@{windows_pid=$taskWorker.Id;started=(Get-Date).ToString('o');scope='Four new native 120-step output/retention diagnostics on historical two-worker count; no full science controls'}
[IO.File]::WriteAllText($taskRecord,($taskReport | ConvertTo-Json))
$taskReport
