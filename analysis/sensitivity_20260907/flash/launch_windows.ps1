$ErrorActionPreference='Stop'
$taskFolder='C:\Users\kaanb\CloudCrushing\sensitivity_20260907\flash'
$taskRecord=Join-Path $taskFolder 'worker_windows.json'
if(Test-Path -LiteralPath $taskRecord){throw 'Existing worker record requires review'}
$taskWorker=Start-Process -FilePath 'wsl.exe' -ArgumentList @('-d','Ubuntu','--exec','env','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1','/home/kaan/venv/bin/python','/mnt/c/Users/kaanb/CloudCrushing/sensitivity_20260907/flash/run_flash.py') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $taskFolder 'worker_windows.log') -RedirectStandardError (Join-Path $taskFolder 'worker_windows.err.log')
[pscustomobject]@{windows_pid=$taskWorker.Id;started=(Get-Date).ToString('o');script='/mnt/c/Users/kaanb/CloudCrushing/sensitivity_20260907/flash/run_flash.py'} | ConvertTo-Json | Set-Content -LiteralPath $taskRecord -Encoding utf8
Start-Sleep -Seconds 3
$taskWorker.Refresh()
if($taskWorker.HasExited){throw 'Worker exited; inspect logs'}
Get-Content -LiteralPath $taskRecord
