$ErrorActionPreference='Stop'
$taskFolder='C:\Users\kaanb\CloudCrushing\sensitivity_20260907\gadget4'
$taskRecord=Join-Path $taskFolder 'smoke_worker_windows.json'
if(Test-Path -LiteralPath $taskRecord){throw 'Existing smoke worker record requires review'}
$taskNative='\\wsl.localhost\Ubuntu\home\kaan\sensitivity_20260907\gadget4'
$taskBuild=Get-Content -Raw -LiteralPath (Join-Path $taskNative 'build.json') | ConvertFrom-Json
if($taskBuild.status -ne 'pinned_not_evolved_validated' -or $taskBuild.tests.returncode -ne 0){throw 'Unverified preparation'}
foreach($taskFile in $taskBuild.pinned_files.PSObject.Properties){
  if((Get-FileHash -LiteralPath (Join-Path $taskNative $taskFile.Name)).Hash.ToLower() -ne $taskFile.Value){throw 'Frozen preparation file changed'}
}
if(Test-Path -LiteralPath (Join-Path $taskNative 'smoke_batch.json')){throw 'Existing native smoke batch cannot be relaunched'}
$taskWorker=Start-Process -FilePath 'wsl.exe' -ArgumentList @('-d','Ubuntu','--exec','env','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1','/home/kaan/venv/bin/python','/home/kaan/sensitivity_20260907/gadget4/gadget_controls.py','smoke') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $taskFolder 'smoke_worker_windows.log') -RedirectStandardError (Join-Path $taskFolder 'smoke_worker_windows.err.log')
[pscustomobject]@{windows_pid=$taskWorker.Id;started=(Get-Date).ToString('o');scope='Two native L3 validation smokes only; no full science queue';script='/home/kaan/sensitivity_20260907/gadget4/gadget_controls.py'} | ConvertTo-Json | Set-Content -LiteralPath $taskRecord -Encoding utf8
Start-Sleep -Seconds 2
$taskWorker.Refresh()
if($taskWorker.HasExited -and $taskWorker.ExitCode -ne 0){throw 'Native smoke worker failed; inspect ledgers and preserve attempts'}
Get-Content -LiteralPath $taskRecord
