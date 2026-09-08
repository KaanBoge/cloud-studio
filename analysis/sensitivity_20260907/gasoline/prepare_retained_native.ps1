$ErrorActionPreference='Stop'
$taskRoot='\\wsl.localhost\Ubuntu\home\kaan\sensitivity_20260907\gasoline'
$taskFrom=Join-Path $taskRoot 'native'
$taskTo=Join-Path $taskRoot 'native_retained'
if(Test-Path -LiteralPath $taskTo){throw 'Existing isolated checkpoint build must not be overwritten'}
if((Get-FileHash -LiteralPath (Join-Path $taskFrom 'gasoline\gasoline')).Hash.ToLower() -ne '7f3018e12f821fe9f74ae2617d80b11cf1e7f7feedd8040ceafc01822a21789e'){throw 'Earlier hook build changed'}
$taskRows=@()
foreach($taskRel in @('gasoline','mdl\mpi')){
  $taskDest=Join-Path $taskTo $taskRel
  New-Item -ItemType Directory -Path $taskDest | Out-Null
  foreach($taskFile in Get-ChildItem -LiteralPath (Join-Path $taskFrom $taskRel) -File){
    $taskTarget=Join-Path $taskDest $taskFile.Name
    Copy-Item -LiteralPath $taskFile.FullName -Destination $taskTarget
    $taskHash=(Get-FileHash -LiteralPath $taskFile.FullName).Hash.ToLower()
    if((Get-FileHash -LiteralPath $taskTarget).Hash.ToLower() -ne $taskHash){throw 'Copy hash mismatch'}
    $taskRows+=[pscustomobject]@{source=$taskFile.FullName;copy=$taskTarget;sha256=$taskHash}
  }
}
[IO.File]::WriteAllText((Join-Path $taskRoot 'retained_copy_manifest.json'),($taskRows | ConvertTo-Json -Depth 5))
[pscustomobject]@{status='new_isolated_copies_only';files=$taskRows.Count}
