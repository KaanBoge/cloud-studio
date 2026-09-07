$ErrorActionPreference = 'Stop'
$taskFolder = 'C:\Users\kaanb\CloudCrushing\sensitivity_20260907\enzo'
$taskRecord = Join-Path $taskFolder 'worker_v2_windows.json'
if (Test-Path -LiteralPath $taskRecord) { throw 'Existing worker record requires review' }
$taskWorker = Start-Process -FilePath 'wsl.exe' -ArgumentList @('-d','Ubuntu','--exec','/home/kaan/venv/bin/python','/mnt/c/Users/kaanb/CloudCrushing/sensitivity_20260907/enzo/run_enzo.py') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $taskFolder 'worker_v2_windows.log') -RedirectStandardError (Join-Path $taskFolder 'worker_v2_windows.err.log')
[pscustomobject]@{windows_pid=$taskWorker.Id;started=(Get-Date).ToString('o');script='/mnt/c/Users/kaanb/CloudCrushing/sensitivity_20260907/enzo/run_enzo.py'} | ConvertTo-Json | Set-Content -LiteralPath $taskRecord -Encoding utf8
Start-Sleep -Seconds 3
$taskWorker.Refresh()
if ($taskWorker.HasExited) { throw 'Worker exited; inspect logs' }
Get-Content -LiteralPath $taskRecord
