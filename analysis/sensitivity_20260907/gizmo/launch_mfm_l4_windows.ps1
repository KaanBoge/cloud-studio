param([ValidateSet('Validate','Run')][string]$Mode='Validate')
$ErrorActionPreference='Stop'
$taskFolder='C:\Users\kaanb\CloudCrushing\sensitivity_20260907\gizmo'
$taskStem=if($Mode -eq 'Run'){'full_mfm_l4_worker_windows'}else{'validation_mfm_l4_worker_windows'}
$taskRecord=Join-Path $taskFolder ($taskStem+'.json')
if(Test-Path -LiteralPath $taskRecord){throw 'Existing worker record requires review'}
$taskBundle='\\wsl.localhost\Ubuntu\home\kaan\sensitivity_20260907\gizmo\runner_mfm_l4_v1'
$taskProof=Get-Content -Raw -LiteralPath (Join-Path $taskBundle 'bundle.json') | ConvertFrom-Json
if($taskProof.status -ne 'tested_for_native_L4_validation_only'){throw 'Unexpected L4 bundle'}
foreach($taskFile in $taskProof.files.PSObject.Properties){
  if((Get-FileHash -LiteralPath (Join-Path $taskBundle $taskFile.Name)).Hash.ToLower() -ne $taskFile.Value){throw 'Frozen L4 runner changed'}
}
if($Mode -eq 'Run'){
  $taskValidation=Get-Content -Raw -LiteralPath '\\wsl.localhost\Ubuntu\home\kaan\sensitivity_20260907\gizmo\validation_mfm_l4_v1\report.json' | ConvertFrom-Json
  if($taskValidation.status -ne 'passed'){throw 'Native L4 validation is not passed'}
}
$taskFlag=if($Mode -eq 'Run'){'--run'}else{'--validate'}
$taskWorker=Start-Process -FilePath 'wsl.exe' -ArgumentList @('-d','Ubuntu','--exec','env','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1','/home/kaan/venv/bin/python','/home/kaan/sensitivity_20260907/gizmo/runner_mfm_l4_v1/mfm_l4_controls.py',$taskFlag) -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $taskFolder ($taskStem+'.log')) -RedirectStandardError (Join-Path $taskFolder ($taskStem+'.err.log'))
[pscustomobject]@{windows_pid=$taskWorker.Id;started=(Get-Date).ToString('o');mode=$Mode;script='/home/kaan/sensitivity_20260907/gizmo/runner_mfm_l4_v1/mfm_l4_controls.py'} | ConvertTo-Json | Set-Content -LiteralPath $taskRecord -Encoding utf8
Start-Sleep -Seconds 2
$taskWorker.Refresh()
if($taskWorker.HasExited -and $taskWorker.ExitCode -ne 0){throw 'Worker exited with an error; inspect native ledger and logs'}
Get-Content -LiteralPath $taskRecord
