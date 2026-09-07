$ErrorActionPreference = 'Stop'
$taskSource = 'C:\Users\kaanb\CloudCrushing\followup_20260907'
$taskRepo = 'C:\Users\kaanb\cloud-studio-repo'
$taskNative = '\\wsl.localhost\Ubuntu\home\kaan\followup_20260907'
$taskEvidence = Join-Path $taskSource 'evidence'
Copy-Item -LiteralPath (Join-Path $taskNative 'evidence\tracking_extended.json') -Destination $taskEvidence
$taskReport = Get-Content -LiteralPath (Join-Path $taskEvidence 'tracking_extended.json') -Raw | ConvertFrom-Json
if (-not $taskReport.execution_completed) { throw 'Extended validation has not completed' }
$taskOutput = Join-Path $taskEvidence 'tracking_extended_inputs'
New-Item -ItemType Directory -Path $taskOutput -Force | Out-Null
foreach ($taskCase in Get-ChildItem -LiteralPath (Join-Path $taskNative 'tracking_validation_v1') -Directory) {
    $taskDest = Join-Path $taskOutput $taskCase.Name
    New-Item -ItemType Directory -Path $taskDest -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $taskCase.FullName 'athinput'),(Join-Path $taskCase.FullName 'run.log'),(Join-Path $taskCase.FullName 'provenance.json') -Destination $taskDest
    Get-ChildItem -LiteralPath $taskCase.FullName -Filter '*.hst' -File | ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination $taskDest }
}
$taskPublished = Join-Path $taskRepo 'analysis\followup_20260907'
foreach ($taskFile in @('README.md','TRACKING_TEST_PLAN.md','TRACKING_RESULTS.md','tracking_validation.py','test_tracking_validation.py','package_tracking.ps1')) {
    Copy-Item -LiteralPath (Join-Path $taskSource $taskFile) -Destination $taskPublished
}
Copy-Item -LiteralPath (Join-Path $taskEvidence 'tracking_extended.json') -Destination (Join-Path $taskPublished 'evidence')
Copy-Item -LiteralPath $taskOutput -Destination (Join-Path $taskPublished 'evidence') -Recurse -Force
Copy-Item -LiteralPath 'C:\Users\kaanb\CloudCrushing\studio\verification.html' -Destination (Join-Path $taskRepo 'verification.html')
Write-Output 'Packaged completed tracking tests and explicit retention failures. Native fields remain in WSL.'
