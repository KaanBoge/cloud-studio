$ErrorActionPreference='Stop'
$src='C:\Users\kaanb\CloudCrushing\performance_20260907c'
$dst='C:\Users\kaanb\cloud-studio-repo\analysis\performance_20260907c'
New-Item -ItemType Directory -Path $dst -Force | Out-Null
foreach($name in @('README.md','PLAN.md','probe.py','report.json','lossless_probe.py','lossless_probe.json','campaign_inventory.py','campaign_inventory.json','deploy_profile.sh','update_queue.py')) {
    Copy-Item -LiteralPath (Join-Path $src $name) -Destination (Join-Path $dst $name)
}
$queueDst='C:\Users\kaanb\cloud-studio-repo\analysis\restart_20260907'
New-Item -ItemType Directory -Path $queueDst -Force | Out-Null
foreach($name in @('run_l4.py','queue_more.py','test_l4.py','test_queue.py')) {
    Copy-Item -LiteralPath ('C:\Users\kaanb\CloudCrushing\restart_20260907\'+$name) -Destination (Join-Path $queueDst $name)
}
Copy-Item -LiteralPath 'C:\Users\kaanb\CloudCrushing\performance_20260907\README.md' -Destination 'C:\Users\kaanb\cloud-studio-repo\analysis\performance_20260907\README.md'
Copy-Item -LiteralPath 'C:\Users\kaanb\CloudCrushing\performance_20260907\optimized_profiles.json' -Destination 'C:\Users\kaanb\cloud-studio-repo\analysis\performance_20260907\optimized_profiles.json'
