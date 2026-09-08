$ErrorActionPreference='Stop'
$taskStudy='C:\Users\kaanb\CloudCrushing\sensitivity_20260907\gadget4'
$taskRaw='C:\Users\kaanb\CloudCrushing\native_runs\sensitivity_20260907\gadget4_L4_velocity_pair_v1'
$taskNative='\\wsl.localhost\Ubuntu\home\kaan\sensitivity_20260907\gadget4\runner_full_l4_ntfs_v1'
$taskPlanPath=Join-Path $taskNative 'plan.json'
$taskExpectedPlan='a66c291cdaf6858a0c69560a47ed137f5d026e85851af205134b5cb0d67bdba4'
$taskRecord=Join-Path $taskStudy 'l4_direct_storage_worker.json'
foreach($taskPath in @($taskRecord,(Join-Path $taskRaw 'batch.json'),(Join-Path $taskRaw 'windows_readback.json'))){
 if(Test-Path -LiteralPath $taskPath){throw ('Existing preparation/worker state: '+$taskPath)}
}
if((Get-FileHash -LiteralPath $taskPlanPath).Hash.ToLower() -ne $taskExpectedPlan){throw 'Plan hash changed'}
$taskPlan=Get-Content -LiteralPath $taskPlanPath -Raw | ConvertFrom-Json
if($taskPlan.status -ne 'frozen_reviewed_ready_for_windows_readback' -or $taskPlan.tests.returncode -ne 0 -or $taskPlan.tests.output -notmatch 'Ran 15 tests' -or $taskPlan.tests.output -notmatch '\bOK\b'){throw 'Preparation/tests not accepted'}
$taskHashes=@{}
foreach($taskFile in $taskPlan.windows_readback_files.PSObject.Properties){
 $taskTarget=[IO.Path]::GetFullPath((Join-Path $taskRaw $taskFile.Name))
 if(!$taskTarget.StartsWith($taskRaw+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Unexpected raw readback path'}
 $taskDigest=(Get-FileHash -LiteralPath $taskTarget).Hash.ToLower()
 if($taskDigest -ne $taskFile.Value){throw ('Windows readback failed: '+$taskTarget)}
 $taskHashes[$taskFile.Name]=$taskDigest
}
if($taskHashes.Count -ne 5){throw 'Missing probe/IC/parameter readback'}
foreach($taskLaw in @('sharp13','tanh13')){
 $taskFolder=Join-Path $taskRaw $taskLaw
 if(Test-Path -LiteralPath (Join-Path $taskFolder 'output')){throw 'Native outputs already exist'}
 if(Test-Path -LiteralPath (Join-Path $taskFolder 'result.json')){throw 'Case already attempted'}
}
$taskReadback=[ordered]@{status='windows_full_readback_passed';plan_sha256=$taskExpectedPlan;checked_at_utc=[DateTime]::UtcNow.ToString('o');hashes=$taskHashes;native_runs_started=0}
[IO.File]::WriteAllText((Join-Path $taskRaw 'windows_readback.json'),($taskReadback|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
# The runner rechecks both filesystems, both locks, live solvers, all pins and RAM.
$taskWorker=Start-Process -FilePath 'wsl.exe' -ArgumentList @('-d','Ubuntu','--exec','env','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1','MKL_NUM_THREADS=1','/home/kaan/venv/bin/python','/home/kaan/sensitivity_20260907/gadget4/runner_full_l4_ntfs_v1/run_l4_direct_storage.py') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $taskStudy 'l4_direct_storage_worker.log') -RedirectStandardError (Join-Path $taskStudy 'l4_direct_storage_worker.err.log')
$taskState=[ordered]@{windows_pid=$taskWorker.Id;windows_start_time=$taskWorker.StartTime.ToUniversalTime().ToString('o');started_utc=[DateTime]::UtcNow.ToString('o');plan_sha256=$taskExpectedPlan;runner='/home/kaan/sensitivity_20260907/gadget4/runner_full_l4_ntfs_v1/run_l4_direct_storage.py';raw_directory=$taskRaw;scope='Only fresh Gadget-4 L4 sharp/historical pair, chi100 Mach2, eight CPU ranks. No native rebuild, old raw relocation/deletion or blanket queue. Independently validated outputs remain subject to pair checks.'}
[IO.File]::WriteAllText($taskRecord,($taskState|ConvertTo-Json -Depth 6),[Text.UTF8Encoding]::new($false))
$taskWorker.Refresh()
if($taskWorker.HasExited -and $taskWorker.ExitCode -ne 0){throw 'Worker failed; inspect retained logs, do not relaunch'}
$taskState|ConvertTo-Json -Compress
