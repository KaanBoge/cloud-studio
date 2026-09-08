$ErrorActionPreference='Stop'
$taskNative='\\wsl.localhost\Ubuntu\home\kaan\sensitivity_20260907\gasoline'
$taskSource='\\wsl.localhost\Ubuntu\home\kaan\codes\gasoline'
$taskMdl='\\wsl.localhost\Ubuntu\home\kaan\codes\mdl\mpi'
if(Test-Path -LiteralPath $taskNative){throw 'Existing native preparation must not be overwritten'}
$taskSha=(Get-FileHash -LiteralPath (Join-Path $taskSource 'gasoline')).Hash.ToLower()
if($taskSha -ne 'c7645e1774fb4a18fc68bac615ba03f24c83d06dfe4addfbbbc7df2cc4930bb5'){throw 'Native binary changed; review required'}
$taskDest=Join-Path $taskNative 'native\gasoline'
$taskMdlDest=Join-Path $taskNative 'native\mdl\mpi'
New-Item -ItemType Directory -Path $taskDest,$taskMdlDest | Out-Null
$taskRows=@()
foreach($taskPair in @(@($taskSource,$taskDest),@($taskMdl,$taskMdlDest))){
  foreach($taskFile in Get-ChildItem -LiteralPath $taskPair[0] -File){
    if($taskFile.Extension -notin @('.c','.h','.o','.fdl') -and $taskFile.Name -notin @('Makefile','gasoline')){continue}
    $taskTarget=Join-Path $taskPair[1] $taskFile.Name
    Copy-Item -LiteralPath $taskFile.FullName -Destination $taskTarget
    $taskBefore=(Get-FileHash -LiteralPath $taskFile.FullName).Hash.ToLower()
    if((Get-FileHash -LiteralPath $taskTarget).Hash.ToLower() -ne $taskBefore){throw 'Copy hash mismatch'}
    $taskRows+=[pscustomobject]@{source=$taskFile.FullName;copy=$taskTarget;sha256=$taskBefore;bytes=$taskFile.Length}
  }
}
Copy-Item -LiteralPath (Join-Path $taskSource 'gasoline') -Destination (Join-Path $taskNative 'gasoline_original')
foreach($taskMode in @('tanh13','sharp13')){
  $taskFrom=if($taskMode -eq 'tanh13'){'C:\Users\kaanb\CloudCrushing\audit_20260907\before\home\kaan\codes\gasoline\ics'}else{Join-Path $taskSource 'ics'}
  $taskTo=Join-Path $taskNative ('generators\'+$taskMode)
  New-Item -ItemType Directory -Path $taskTo | Out-Null
  foreach($taskName in @('make_gasoline_cloudwind.py','make_gasoline_cloudwind_3d.py')){
    $taskFromFile=Join-Path $taskFrom $taskName
    $taskToFile=Join-Path $taskTo $taskName
    Copy-Item -LiteralPath $taskFromFile -Destination $taskToFile
    $taskHash=(Get-FileHash -LiteralPath $taskFromFile).Hash.ToLower()
    if((Get-FileHash -LiteralPath $taskToFile).Hash.ToLower() -ne $taskHash){throw 'Generator copy mismatch'}
    $taskRows+=[pscustomobject]@{source=$taskFromFile;copy=$taskToFile;sha256=$taskHash;bytes=(Get-Item -LiteralPath $taskFromFile).Length}
  }
}
$taskReport=[pscustomobject]@{status='isolated_byte_copies_only_not_validated';created=(Get-Date).ToString('o');original_binary_sha256=$taskSha;files=$taskRows}
$taskJson=$taskReport | ConvertTo-Json -Depth 8
[System.IO.File]::WriteAllText((Join-Path $taskNative 'copy_manifest.json'),$taskJson)
[System.IO.File]::WriteAllText((Join-Path $PSScriptRoot 'copy_manifest.json'),$taskJson)
$taskReport | Select-Object status,created,original_binary_sha256
