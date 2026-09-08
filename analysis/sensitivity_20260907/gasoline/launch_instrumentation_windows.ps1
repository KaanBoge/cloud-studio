$ErrorActionPreference='Stop'
$taskRoot='\\wsl.localhost\Ubuntu\home\kaan\sensitivity_20260907\gasoline'
$taskRecord=Join-Path $PSScriptRoot 'instrumentation_worker_windows.json'
if(Test-Path -LiteralPath $taskRecord){throw 'Existing launch record; check actual processes, do not relaunch'}
$taskBundle=Get-Content -Raw -LiteralPath (Join-Path $taskRoot 'runner_instrumentation_v1\bundle.json') | ConvertFrom-Json
if($taskBundle.status -ne 'tested_frozen_instrumentation_only'){throw 'Unreviewed runner'}
foreach($taskFile in $taskBundle.pinned_files.PSObject.Properties){
  $taskPath='\\wsl.localhost\Ubuntu'+$taskFile.Name.Replace('/','\')
  if((Get-FileHash -LiteralPath $taskPath).Hash.ToLower() -ne $taskFile.Value){throw 'Frozen file changed'}
}
foreach($taskName in @('original_tanh','off_tanh','on_tanh','on_sharp')){
  if(Test-Path -LiteralPath (Join-Path $taskRoot ('instrumentation_v1\'+$taskName+'\run_started.json'))){throw 'Existing native test; no automatic restart'}
}
$taskWorker=Start-Process -FilePath 'wsl.exe' -ArgumentList @('-d','Ubuntu','--exec','env','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1','/home/kaan/venv/bin/python','/home/kaan/sensitivity_20260907/gasoline/runner_instrumentation_v1/gasoline_controls.py','run') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $PSScriptRoot 'instrumentation_worker.log') -RedirectStandardError (Join-Path $PSScriptRoot 'instrumentation_worker.err.log')
$taskReport=[pscustomobject]@{windows_pid=$taskWorker.Id;started=(Get-Date).ToString('o');scope='Four isolated six-step native Gasoline instrumentation tests, not full science runs'}
[IO.File]::WriteAllText($taskRecord,($taskReport | ConvertTo-Json))
$taskReport
