$ErrorActionPreference='Stop'
$taskFrom='C:\Users\kaanb\CloudCrushing\sensitivity_20260907\arepo'
$taskTo='C:\Users\kaanb\cloud-studio-repo\analysis\sensitivity_20260907\arepo'
$taskSetup=Get-Content -LiteralPath (Join-Path $taskFrom 'setup_validation.json') -Raw | ConvertFrom-Json
$taskYt=Get-Content -LiteralPath (Join-Path $taskFrom 'yt_smoke_validation.json') -Raw | ConvertFrom-Json
$taskSmoke=Get-Content -LiteralPath (Join-Path $taskFrom 'smoke_batch_v2.json') -Raw | ConvertFrom-Json
if($taskSetup.status -ne 'passed' -or $taskYt.status -ne 'passed' -or $taskYt.checks.Count -ne 4){throw 'Setup verification missing'}
if((Get-FileHash -LiteralPath (Join-Path $taskFrom 'run_arepo.py')).Hash.ToLower() -ne $taskSetup.launcher_sha256){throw 'Launcher differs from verified version'}
if($taskSmoke.status -ne 'complete_native_checks' -or $taskSmoke.finished.Count -ne 2 -or ($taskSmoke.finished | Where-Object {$_.status -ne 'complete_native_checks'})){throw 'Native smoke pair incomplete'}
if(Test-Path -LiteralPath $taskTo){throw 'Publication directory already exists; review before updating'}
$taskNames=@('README.md','experiment.json','setup_arepo.py','run_arepo.py','run_arepo_failed_smoke_v1.py','test_arepo.py','verify_setup.py','verify_yt_smokes.py','launch_windows.ps1','analyze_arepo.py','test_analysis_arepo.py','build.json','smoke_batch.json','smoke_batch_v2.json','setup_validation.json','yt_smoke_validation.json','generator_sharp.py','generator_historical.py','param_L3.txt','param_L4.txt','param_L5.txt','Config.sh','stage_publication.ps1')
foreach($taskName in $taskNames){if(!(Test-Path -LiteralPath (Join-Path $taskFrom $taskName) -PathType Leaf)){throw "Missing $taskName"}}
New-Item -ItemType Directory -Path $taskTo | Out-Null
foreach($taskName in $taskNames){
  $taskSource=Join-Path $taskFrom $taskName
  $taskTarget=Join-Path $taskTo $taskName
  Copy-Item -LiteralPath $taskSource -Destination $taskTarget
  if((Get-FileHash -LiteralPath $taskSource).Hash -ne (Get-FileHash -LiteralPath $taskTarget).Hash){throw "Hash mismatch: $taskName"}
}
'Staged verified Arepo setup/scripts only, not completed full results, solver source/binaries, native datasets or viewer entries.'
