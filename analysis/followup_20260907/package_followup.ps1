$ErrorActionPreference = 'Stop'
$taskSource = 'C:\Users\kaanb\CloudCrushing'
$taskRepo = 'C:\Users\kaanb\cloud-studio-repo'
$taskNative = '\\wsl.localhost\Ubuntu\home\kaan\followup_20260907'
$taskEvidence = Join-Path $taskSource 'followup_20260907\evidence'
New-Item -ItemType Directory -Path $taskEvidence -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $taskNative 'evidence') -Destination (Join-Path $taskSource 'followup_20260907') -Recurse -Force
Copy-Item -LiteralPath (Join-Path $taskNative 'logs') -Destination $taskEvidence -Recurse -Force
$taskCooling = Join-Path $taskEvidence 'cooling_inputs'
New-Item -ItemType Directory -Path $taskCooling -Force | Out-Null
$taskAudit = Get-Content -LiteralPath (Join-Path $taskEvidence 'cooling_audit.json') -Raw | ConvertFrom-Json
foreach ($taskRun in $taskAudit.runs) {
    $taskDir = '\\wsl.localhost\Ubuntu' + $taskRun.run_dir.Replace('/','\')
    $taskDest = Join-Path $taskCooling (Split-Path -Leaf $taskDir)
    New-Item -ItemType Directory -Path $taskDest -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $taskDir 'athinput'),(Join-Path $taskDir 'run.out') -Destination $taskDest
}
foreach ($taskCase in Get-ChildItem -LiteralPath (Join-Path $taskNative 'tracking_tests_v2') -Directory) {
    $taskDest = Join-Path $taskEvidence ('tracking_inputs\' + $taskCase.Name)
    New-Item -ItemType Directory -Path $taskDest -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $taskCase.FullName 'athinput'),(Join-Path $taskCase.FullName 'run.log'),(Join-Path $taskCase.FullName 'verification.json') -Destination $taskDest
}
$taskTests = Get-Content -LiteralPath (Join-Path $taskEvidence 'regression_suite.json') -Raw | ConvertFrom-Json
if (-not $taskTests.passed) { throw 'Tests not passed; do not package' }
foreach ($taskFile in @('comparison_checks.py','storage_guard.py','run_corrected_athpp.py','figure1_v2.py','figure2_v2.py','diagnostics_v2.py','test_viewer.cjs','README.md')) {
    Copy-Item -LiteralPath (Join-Path $taskSource ('audit_20260907\'+$taskFile)) -Destination (Join-Path $taskRepo ('analysis\verified_20260907\'+$taskFile))
}
foreach ($taskFile in @('run_optimized.py','README.md')) {
    Copy-Item -LiteralPath (Join-Path $taskSource ('performance_20260907\'+$taskFile)) -Destination (Join-Path $taskRepo ('analysis\performance_20260907\'+$taskFile))
}
$taskDest = Join-Path $taskRepo 'analysis\followup_20260907'
New-Item -ItemType Directory -Path $taskDest -Force | Out-Null
Get-ChildItem -LiteralPath (Join-Path $taskSource 'followup_20260907') -File | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $taskDest
}
Copy-Item -LiteralPath $taskEvidence -Destination $taskDest -Recurse -Force
Copy-Item -LiteralPath (Join-Path $taskSource 'audit_20260907\ANALYSIS_README.md') -Destination (Join-Path $taskRepo 'analysis\README.md')
foreach ($taskFile in @('viewer.html','verification.html')) {
    Copy-Item -LiteralPath (Join-Path $taskSource ('studio\'+$taskFile)) -Destination (Join-Path $taskRepo $taskFile)
}
Write-Output 'Packaged scripts and text evidence; no native fields, binaries, backups or deleted data included.'
