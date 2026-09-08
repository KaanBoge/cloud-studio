$ErrorActionPreference='Stop'
$taskStudy='C:\Users\kaanb\CloudCrushing\sensitivity_20260907\gizmo'
$taskRaw='C:\Users\kaanb\CloudCrushing\native_runs\sensitivity_20260907\mfv_L4_velocity_pair_v1'
$taskNative='\\wsl.localhost\Ubuntu\home\kaan\sensitivity_20260907\gizmo\mfv_timestep_repair_v1\l4_full_runner_v1'
$taskExpected='2b77bb64257e2826dfe241ca6fb31eedcd5b868d73eeb4761cf96ac079430d7c'
$taskRecord=Join-Path $taskStudy 'mfv_l4_full_worker.json'
foreach($taskPath in @($taskRecord,(Join-Path $taskRaw 'batch.json'),(Join-Path $taskRaw 'windows_readback.json'))){if(Test-Path -LiteralPath $taskPath){throw ('Existing full launch state: '+$taskPath)}}
$taskPlanPath=Join-Path $taskNative 'plan.json'
if((Get-FileHash -LiteralPath $taskPlanPath).Hash.ToLower() -ne $taskExpected){throw 'Full plan changed'}
$taskPlan=Get-Content -LiteralPath $taskPlanPath -Raw | ConvertFrom-Json
if($taskPlan.status -ne 'frozen_L4_full_pair_needs_windows_readback' -or $taskPlan.tests -ne 7 -or $taskPlan.native_controls_started -ne 0 -or $taskPlan.preparation_sha256 -ne '77768badc2721247f471c251ef7e316d02060eabf3e76c549dadcbd367e842c2'){throw 'Wrong full admission evidence'}
$taskHashes=@{}
foreach($taskEntry in $taskPlan.windows_readback_files.PSObject.Properties){
 $taskTarget=[IO.Path]::GetFullPath((Join-Path $taskRaw $taskEntry.Name))
 if(!$taskTarget.StartsWith($taskRaw+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Wrong full readback path'}
 $taskDigest=(Get-FileHash -LiteralPath $taskTarget).Hash.ToLower()
 if($taskDigest -ne $taskEntry.Value){throw 'Windows full readback mismatch'}
 $taskHashes[$taskEntry.Name]=$taskDigest
}
if($taskHashes.Count -ne 4){throw 'Missing full IC/input readback'}
foreach($taskLaw in @('sharp13','tanh13')){
 foreach($taskName in @('output','result.json')){if(Test-Path -LiteralPath (Join-Path $taskRaw ($taskLaw+'/'+$taskName))){throw 'Full native case already attempted'}}
}
$taskProof=[ordered]@{status='windows_readback_passed';plan_sha256=$taskExpected;hashes=$taskHashes;checked_at_utc=[DateTime]::UtcNow.ToString('o');scope='Both full L4 ICs and identical parameters independently checked before launch.'}
[IO.File]::WriteAllText((Join-Path $taskRaw 'windows_readback.json'),($taskProof|ConvertTo-Json -Depth 6),[Text.UTF8Encoding]::new($false))
$taskWorker=Start-Process -FilePath 'wsl.exe' -ArgumentList @('-d','Ubuntu','--exec','env','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1','MKL_NUM_THREADS=1','/home/kaan/venv/bin/python','/home/kaan/sensitivity_20260907/gizmo/mfv_timestep_repair_v1/l4_full_runner_v1/mfv_l4_full.py','run') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $taskStudy 'mfv_l4_full_worker.log') -RedirectStandardError (Join-Path $taskStudy 'mfv_l4_full_worker.err.log')
$taskState=[ordered]@{windows_pid=$taskWorker.Id;windows_started_utc=$taskWorker.StartTime.ToUniversalTime().ToString('o');plan_sha256=$taskExpected;runner='/home/kaan/sensitivity_20260907/gizmo/mfv_timestep_repair_v1/l4_full_runner_v1/mfv_l4_full.py';raw_directory=$taskRaw;scope='Fresh repaired MFV L4 sharp/historical full pair on eight CPU ranks; each targets5tcc with0.05tcc output cadence. Second follows first only after native checks pass. No old rerun, raw deletion, native rebuild or blanket queue.'}
[IO.File]::WriteAllText($taskRecord,($taskState|ConvertTo-Json -Depth 6),[Text.UTF8Encoding]::new($false))
$taskWorker.Refresh()
if($taskWorker.HasExited -and $taskWorker.ExitCode -ne 0){throw 'Full worker failed; inspect retained logs, do not relaunch'}
$taskState | ConvertTo-Json -Compress
