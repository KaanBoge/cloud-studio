$ErrorActionPreference='Stop'
$taskFolder='C:\Users\kaanb\CloudCrushing\sensitivity_20260907\gadget4'
$taskRecord=Join-Path $taskFolder 'l4_validation_worker_windows.json'
if(Test-Path -LiteralPath $taskRecord){throw 'Existing worker record requires live review'}
$taskNative='\\wsl.localhost\Ubuntu\home\kaan\sensitivity_20260907\gadget4'
$taskBundle=Get-Content -Raw -LiteralPath (Join-Path $taskNative 'runner_validation_l4_v2\bundle.json') | ConvertFrom-Json
if($taskBundle.status -ne 'tested_L4_validation_only'){throw 'Unreviewed validation runner'}
foreach($taskFile in $taskBundle.pinned_files.PSObject.Properties){
  $taskPath='\\wsl.localhost\Ubuntu'+$taskFile.Name.Replace('/','\')
  if((Get-FileHash -LiteralPath $taskPath).Hash.ToLower() -ne $taskFile.Value){throw 'Frozen validation file changed'}
}
if(Test-Path -LiteralPath (Join-Path $taskNative 'validation_l4_v1')){throw 'Existing validation cannot be relaunched'}
$taskWorker=Start-Process -FilePath 'wsl.exe' -ArgumentList @('-d','Ubuntu','--exec','env','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1','/home/kaan/venv/bin/python','/home/kaan/sensitivity_20260907/gadget4/runner_validation_l4_v2/gadget_l4_controls.py') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $taskFolder 'l4_validation_worker_windows.log') -RedirectStandardError (Join-Path $taskFolder 'l4_validation_worker_windows.err.log')
[pscustomobject]@{windows_pid=$taskWorker.Id;started=(Get-Date).ToString('o');scope='Two short native Gadget-4 L4 checks and measured storage audit, not full science runs';script='/home/kaan/sensitivity_20260907/gadget4/runner_validation_l4_v2/gadget_l4_controls.py'} | ConvertTo-Json | Set-Content -LiteralPath $taskRecord -Encoding utf8
Start-Sleep -Seconds 2
$taskWorker.Refresh()
if($taskWorker.HasExited -and $taskWorker.ExitCode -ne 0){throw 'Validation worker failed; inspect preserved logs'}
Get-Content -LiteralPath $taskRecord
