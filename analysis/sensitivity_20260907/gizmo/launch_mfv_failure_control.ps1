$ErrorActionPreference='Stop'
$taskFolder='C:\Users\kaanb\CloudCrushing\sensitivity_20260907\gizmo'
$taskRecord=Join-Path $taskFolder 'mfv_historical_worker_windows.json'
if(Test-Path -LiteralPath $taskRecord){throw 'Existing worker record requires review'}
$taskWorker=Start-Process -FilePath 'wsl.exe' -ArgumentList @('-d','Ubuntu','--exec','env','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1','/home/kaan/venv/bin/python','/mnt/c/Users/kaanb/CloudCrushing/sensitivity_20260907/gizmo/run_mfv_failure_control.py') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $taskFolder 'mfv_historical_worker_windows.log') -RedirectStandardError (Join-Path $taskFolder 'mfv_historical_worker_windows.err.log')
[pscustomobject]@{windows_pid=$taskWorker.Id;started=(Get-Date).ToString('o');script='/mnt/c/Users/kaanb/CloudCrushing/sensitivity_20260907/gizmo/run_mfv_failure_control.py';scope='Never-started historical MFV failure-control; no changed numerics or checkpoint resume'}|ConvertTo-Json|Set-Content -LiteralPath $taskRecord -Encoding utf8
Start-Sleep -Seconds 3
$taskWorker.Refresh()
if($taskWorker.HasExited){throw 'Worker exited; inspect actual result and logs'}
Get-Content -LiteralPath $taskRecord
