$ErrorActionPreference='Stop'
$taskScript='\\wsl.localhost\Ubuntu\home\kaan\sensitivity_20260907\gasoline\test_native_repeatability.py'
$taskRecord=Join-Path $PSScriptRoot 'repeatability_worker_windows.json'
if(Test-Path -LiteralPath $taskRecord){throw 'Existing launch record'}
if(Test-Path -LiteralPath '\\wsl.localhost\Ubuntu\home\kaan\sensitivity_20260907\gasoline\repeatability_v1'){throw 'Existing native diagnostic'}
$taskHash=(Get-FileHash -LiteralPath $taskScript).Hash.ToLower()
if($taskHash -ne (Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'test_native_repeatability.py')).Hash.ToLower()){throw 'Script hash mismatch'}
$taskWorker=Start-Process -FilePath 'wsl.exe' -ArgumentList @('-d','Ubuntu','--exec','env','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1','/home/kaan/venv/bin/python','/home/kaan/sensitivity_20260907/gasoline/test_native_repeatability.py') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $PSScriptRoot 'repeatability_worker.log') -RedirectStandardError (Join-Path $PSScriptRoot 'repeatability_worker.err.log')
$taskReport=[pscustomobject]@{windows_pid=$taskWorker.Id;started=(Get-Date).ToString('o');script_sha256=$taskHash;scope='Two new six-step repeats of unchanged original Gasoline, no full science controls'}
[IO.File]::WriteAllText($taskRecord,($taskReport | ConvertTo-Json))
$taskReport
