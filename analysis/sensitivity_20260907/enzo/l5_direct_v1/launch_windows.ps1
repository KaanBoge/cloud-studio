param([ValidateSet('diagnostics','full')][string]$Stage='diagnostics')
$ErrorActionPreference='Stop'
$stageRoot='C:\Users\kaanb\CloudCrushing\sensitivity_20260907\enzo\l5_direct_v1'
$rawRoot='C:\Users\kaanb\CloudCrushing\native_runs\sensitivity_20260907\enzo_L5_velocity_pair_v1'
$record=Join-Path $stageRoot ($Stage+'_worker.json')
if (Test-Path -LiteralPath $record) { throw 'Existing worker record; do not relaunch completed/partial stage' }
$planPath=Join-Path $stageRoot 'plan.json'
$plan=Get-Content -LiteralPath $planPath -Raw | ConvertFrom-Json
$hashes=@{}
foreach ($entry in $plan.windows_files.PSObject.Properties) {
    $target=[IO.Path]::GetFullPath((Join-Path $rawRoot $entry.Name))
    if (-not $target.StartsWith($rawRoot+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid readback target' }
    $digest=(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($digest -ne $entry.Value) { throw ('Windows/Linux file readback mismatch: '+$target) }
    $hashes[$entry.Name]=$digest
}
$proof=[ordered]@{plan_sha256=(Get-FileHash -LiteralPath $planPath -Algorithm SHA256).Hash.ToLowerInvariant(); hashes=$hashes; verified_utc=[DateTime]::UtcNow.ToString('o')}
$proofPath=Join-Path $rawRoot 'windows_readback.json'
if (-not (Test-Path -LiteralPath $proofPath)) {
    [IO.File]::WriteAllText($proofPath,($proof|ConvertTo-Json -Depth 5),[Text.UTF8Encoding]::new($false))
} else {
    $old=Get-Content -LiteralPath $proofPath -Raw|ConvertFrom-Json
    if ($old.plan_sha256 -ne $proof.plan_sha256) { throw 'Changed readback plan' }
}
if ($Stage -eq 'full') {
    $diagnostics=Get-Content -LiteralPath (Join-Path $rawRoot 'diagnostics_batch.json') -Raw|ConvertFrom-Json
    if ($diagnostics.status -ne 'complete_independent_pair_checks') { throw 'L5 diagnostics have not passed' }
}
$tests=Join-Path $stageRoot 'test_result.json'
if (-not (Test-Path -LiteralPath $tests)) { throw 'Test results missing' }
$testRecord=Get-Content -LiteralPath $tests -Raw|ConvertFrom-Json
if ($testRecord.returncode -ne 0 -or $testRecord.plan_sha256 -ne $proof.plan_sha256) { throw 'Tests did not pass for this plan' }
$worker=Start-Process -FilePath 'wsl.exe' -ArgumentList @('-d','Ubuntu','--exec','/home/kaan/venv/bin/python','/mnt/c/Users/kaanb/CloudCrushing/sensitivity_20260907/enzo/l5_direct_v1/runner.py',$Stage) -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $stageRoot ($Stage+'_worker.log')) -RedirectStandardError (Join-Path $stageRoot ($Stage+'_worker.err.log'))
$value=[ordered]@{pid=$worker.Id; started_local=(Get-Date).ToString('o'); stage=$Stage; plan_sha256=$proof.plan_sha256; raw_root=$rawRoot}
[IO.File]::WriteAllText($record,($value|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
Start-Sleep -Seconds 2
$worker.Refresh()
if ($worker.HasExited) { throw 'Worker exited: inspect stage log before further action' }
$value | ConvertTo-Json
