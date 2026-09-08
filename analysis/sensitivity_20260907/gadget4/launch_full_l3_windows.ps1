$ErrorActionPreference='Stop'
$taskFolder='C:\Users\kaanb\CloudCrushing\sensitivity_20260907\gadget4'
$taskRecord=Join-Path $taskFolder 'full_l3_worker_windows.json'
if(Test-Path -LiteralPath $taskRecord){throw 'Existing worker record requires live review'}
$taskNative='\\wsl.localhost\Ubuntu\home\kaan\sensitivity_20260907\gadget4'
$taskBundlePath=Join-Path $taskNative 'runner_l3_v1'
$taskProof=Get-Content -Raw -LiteralPath (Join-Path $taskBundlePath 'bundle.json') | ConvertFrom-Json
if($taskProof.status -ne 'tested_for_full_L3_pair'){throw 'Unreviewed full runner'}
foreach($taskFile in $taskProof.files.PSObject.Properties){
  if((Get-FileHash -LiteralPath (Join-Path $taskBundlePath $taskFile.Name)).Hash.ToLower() -ne $taskFile.Value){throw 'Frozen runner file changed'}
}
if(Test-Path -LiteralPath (Join-Path $taskNative 'full_l3_v1')){throw 'Existing full native batch cannot be relaunched'}
$taskWorker=Start-Process -FilePath 'wsl.exe' -ArgumentList @('-d','Ubuntu','--exec','env','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1','/home/kaan/venv/bin/python','/home/kaan/sensitivity_20260907/gadget4/runner_l3_v1/run_full_l3.py') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $taskFolder 'full_l3_worker_windows.log') -RedirectStandardError (Join-Path $taskFolder 'full_l3_worker_windows.err.log')
[pscustomobject]@{windows_pid=$taskWorker.Id;started=(Get-Date).ToString('o');scope='Native Gadget-4 L3 sharp then historical; fixed chi100/Mach2. Full validation follows each solver run; launch is not accepted completion.';script='/home/kaan/sensitivity_20260907/gadget4/runner_l3_v1/run_full_l3.py'} | ConvertTo-Json | Set-Content -LiteralPath $taskRecord -Encoding utf8
Start-Sleep -Seconds 2
$taskWorker.Refresh()
if($taskWorker.HasExited -and $taskWorker.ExitCode -ne 0){throw 'Worker failed; preserve native batch and inspect logs'}
Get-Content -LiteralPath $taskRecord
