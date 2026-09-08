$ErrorActionPreference='Stop'
$taskFolder='C:\Users\kaanb\CloudCrushing\sensitivity_20260907\gizmo'
$taskRecord=Join-Path $taskFolder 'full_l3_worker_windows.json'
if(Test-Path -LiteralPath $taskRecord){throw 'Existing worker record requires review'}
$taskBundle='\\wsl.localhost\Ubuntu\home\kaan\sensitivity_20260907\gizmo\runner_l3_v1'
$taskProof=Get-Content -Raw -LiteralPath (Join-Path $taskBundle 'bundle.json') | ConvertFrom-Json
if($taskProof.status -ne 'tested_ready_for_guarded_L3_launch'){throw 'Frozen bundle not ready'}
foreach($taskFile in $taskProof.files.PSObject.Properties){
  if((Get-FileHash -LiteralPath (Join-Path $taskBundle $taskFile.Name)).Hash.ToLower() -ne $taskFile.Value){throw 'Frozen runner changed'}
}
$taskWorker=Start-Process -FilePath 'wsl.exe' -ArgumentList @('-d','Ubuntu','--exec','env','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1','/home/kaan/venv/bin/python','/home/kaan/sensitivity_20260907/gizmo/runner_l3_v1/run_full_l3.py','--run') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $taskFolder 'full_l3_worker_windows.log') -RedirectStandardError (Join-Path $taskFolder 'full_l3_worker_windows.err.log')
[pscustomobject]@{windows_pid=$taskWorker.Id;started=(Get-Date).ToString('o');script='/home/kaan/sensitivity_20260907/gizmo/runner_l3_v1/run_full_l3.py';planned_controls=4;level=3}|ConvertTo-Json|Set-Content -LiteralPath $taskRecord -Encoding utf8
Start-Sleep -Seconds 3
$taskWorker.Refresh()
if($taskWorker.HasExited){throw 'Worker exited; inspect actual ledger and logs'}
Get-Content -LiteralPath $taskRecord
