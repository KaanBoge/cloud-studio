$ErrorActionPreference='Stop'
$taskStudy='C:\Users\kaanb\CloudCrushing\sensitivity_20260907\gizmo'
$taskRaw='C:\Users\kaanb\CloudCrushing\native_runs\sensitivity_20260907\mfv_L4_preparation_v1'
$taskNative='\\wsl.localhost\Ubuntu\home\kaan\sensitivity_20260907\gizmo\mfv_timestep_repair_v1\l4_prepare_runner_v1'
$taskExpected='579f85c2ca74cf7e44a8529b77d3d8f80e45e6760ccc18fa9aad9bae7c15e096'
$taskRecord=Join-Path $taskStudy 'mfv_l4_prepare_worker.json'
foreach($taskPath in @($taskRecord,(Join-Path $taskRaw 'batch.json'),(Join-Path $taskRaw 'windows_readback.json'))){
 if(Test-Path -LiteralPath $taskPath){throw ('Existing launch state: '+$taskPath)}
}
$taskPlanPath=Join-Path $taskNative 'plan.json'
if((Get-FileHash -LiteralPath $taskPlanPath).Hash.ToLower() -ne $taskExpected){throw 'Frozen plan changed'}
$taskPlan=Get-Content -LiteralPath $taskPlanPath -Raw | ConvertFrom-Json
if($taskPlan.status -ne 'frozen_short_only_needs_windows_readback' -or $taskPlan.tests -ne 23 -or $taskPlan.cases.Count -ne 6 -or $taskPlan.native_runs_started -ne 0 -or $taskPlan.full_pair_reserved){throw 'Wrong frozen short-only scope'}
$taskHashes=@{}
foreach($taskEntry in $taskPlan.windows_readback_files.PSObject.Properties){
 $taskTarget=[IO.Path]::GetFullPath((Join-Path $taskRaw $taskEntry.Name))
 if(!$taskTarget.StartsWith($taskRaw+'\inputs\',[StringComparison]::OrdinalIgnoreCase)){throw 'Wrong readback path'}
 $taskDigest=(Get-FileHash -LiteralPath $taskTarget).Hash.ToLower()
 if($taskDigest -ne $taskEntry.Value){throw 'Windows readback mismatch'}
 $taskHashes[$taskEntry.Name]=$taskDigest
}
if($taskHashes.Count -ne 6){throw 'Missing IC/input readback'}
foreach($taskCase in $taskPlan.cases){if(Test-Path -LiteralPath (Join-Path $taskRaw $taskCase.name)){throw 'Native case already attempted'}}
$taskProof=[ordered]@{status='windows_readback_passed';plan_sha256=$taskExpected;hashes=$taskHashes;checked_at_utc=[DateTime]::UtcNow.ToString('o');scope='Two L4 ICs and four native parameter templates checked. No full solver controls authorized.'}
[IO.File]::WriteAllText((Join-Path $taskRaw 'windows_readback.json'),($taskProof|ConvertTo-Json -Depth 6),[Text.UTF8Encoding]::new($false))
$taskWorker=Start-Process -FilePath 'wsl.exe' -ArgumentList @('-d','Ubuntu','--exec','env','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1','MKL_NUM_THREADS=1','/home/kaan/venv/bin/python','/home/kaan/sensitivity_20260907/gizmo/mfv_timestep_repair_v1/l4_prepare_runner_v1/mfv_l4_prepare.py','run') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $taskStudy 'mfv_l4_prepare_worker.log') -RedirectStandardError (Join-Path $taskStudy 'mfv_l4_prepare_worker.err.log')
$taskState=[ordered]@{windows_pid=$taskWorker.Id;windows_started_utc=$taskWorker.StartTime.ToUniversalTime().ToString('o');plan_sha256=$taskExpected;runner='/home/kaan/sensitivity_20260907/gizmo/mfv_timestep_repair_v1/l4_prepare_runner_v1/mfv_l4_prepare.py';raw_directory=$taskRaw;scope='Six fresh repaired MFV L4 short/timing diagnostics on eight CPU ranks. No full-pair launch, old rerun, data deletion or native rebuild.'}
[IO.File]::WriteAllText($taskRecord,($taskState|ConvertTo-Json -Depth 6),[Text.UTF8Encoding]::new($false))
$taskWorker.Refresh()
if($taskWorker.HasExited -and $taskWorker.ExitCode -ne 0){throw 'Worker failed; inspect retained logs, do not relaunch'}
$taskState | ConvertTo-Json -Compress
