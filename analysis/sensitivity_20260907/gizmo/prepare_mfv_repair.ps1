$ErrorActionPreference = 'Stop'
$taskNative = '\\wsl.localhost\Ubuntu\home\kaan\codes\gizmo'
$taskStudy = '\\wsl.localhost\Ubuntu\home\kaan\sensitivity_20260907\gizmo'
$taskTarget = Join-Path $taskStudy 'mfv_timestep_repair_v1'
if (Test-Path -LiteralPath $taskTarget) { throw 'Isolated repair directory already exists' }
$taskCommit = (& wsl -d Ubuntu --exec git -C /home/kaan/codes/gizmo rev-parse HEAD).Trim()
if ($taskCommit -ne 'a828c4ba79d67093bd1a3d04f6f90b5d2d94d65f') { throw 'Unexpected native source revision' }
$taskChanges = @(& wsl -d Ubuntu --exec git -C /home/kaan/codes/gizmo diff --name-only)
if (@($taskChanges | Where-Object { $_ -ne 'Makefile.systype' }).Count) { throw 'Unexpected tracked source changes' }
$taskNames = @(& wsl -d Ubuntu --exec git -C /home/kaan/codes/gizmo ls-files)
if ($LASTEXITCODE -ne 0) { throw 'Cannot inventory tracked native files' }
$taskNames = @($taskNames | Where-Object { $_ -match '\.(c|h|f90|dek)$' -or $_ -in @('Makefile','Makefile.systype','config-makefile','prepare-config.perl') })
$taskManifest = @()
$taskBytes = 0L
foreach ($taskName in $taskNames) {
    $taskPath = Join-Path $taskNative $taskName
    $taskFile = Get-Item -LiteralPath $taskPath
    if ($taskFile.LinkType -or $taskName.Contains('..')) { throw 'Unexpected linked or traversing source' }
    $taskBytes += $taskFile.Length
    $taskManifest += [ordered]@{ path=$taskName; bytes=$taskFile.Length; sha256=(Get-FileHash -LiteralPath $taskPath).Hash.ToLower() }
}
if ($taskBytes -gt 100MB) { throw 'Unexpectedly large source selection' }
New-Item -ItemType Directory -Path $taskTarget | Out-Null
foreach ($taskVariant in @('reference','repaired','mfm_probe')) {
    $taskTree = Join-Path $taskTarget $taskVariant
    New-Item -ItemType Directory -Path $taskTree | Out-Null
    foreach ($taskEntry in $taskManifest) {
        $taskDestination = Join-Path $taskTree $taskEntry.path
        New-Item -ItemType Directory -Path (Split-Path $taskDestination) -Force | Out-Null
        Copy-Item -LiteralPath (Join-Path $taskNative $taskEntry.path) -Destination $taskDestination
        if ((Get-FileHash -LiteralPath $taskDestination).Hash.ToLower() -ne $taskEntry.sha256) { throw 'Source copy mismatch' }
    }
    $taskConfig = if ($taskVariant -eq 'mfm_probe') { 'Config_mfm.sh' } else { 'Config_mfv.sh' }
    Copy-Item -LiteralPath (Join-Path $taskStudy $taskConfig) -Destination (Join-Path $taskTree 'Config.sh')
}
$taskRecord = [ordered]@{ status='source_copies_only_not_built'; source_commit=$taskCommit; source_root='/home/kaan/codes/gizmo'; selected_source_bytes=$taskBytes; copied_variants=@('reference','repaired','mfm_probe'); source_files=$taskManifest; native_simulations_started=0; original_binaries_changed=0; created_at_utc=[DateTime]::UtcNow.ToString('o') }
[IO.File]::WriteAllText((Join-Path $taskTarget 'source_manifest.json'), ($taskRecord | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))
[pscustomobject]$taskRecord | Select-Object status,selected_source_bytes,native_simulations_started | ConvertTo-Json -Compress
