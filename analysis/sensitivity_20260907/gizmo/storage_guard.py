"""Conservative free-space checks for native runs, including WSL's backing drive.

WSL's ext4 free space is not the free space of the Windows volume containing its
growing VHDX. Check both. An unavailable host measurement fails closed on WSL.
Nothing is deleted, compacted, moved, or signalled by this module.
"""
import base64
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess

GIB = 1024**3
HOST_QUERY = r'''
$ErrorActionPreference = 'Stop'
$records = @(Get-ChildItem -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss' | ForEach-Object {
  $distro = Get-ItemProperty -LiteralPath $_.PSPath
  $base = $distro.BasePath -replace '^\\\\\?\\', ''
  if ($base -notmatch '^([A-Za-z]):\\') { throw 'Unsupported WSL backing path' }
  $letter = $Matches[1]
  $drive = [System.IO.DriveInfo]::new($letter + ':\')
  [pscustomobject]@{distribution=$distro.DistributionName; base_path=$base;
    drive=($letter + ':'); free_bytes=$drive.AvailableFreeSpace; total_bytes=$drive.TotalSize}
})
ConvertTo-Json -InputObject $records -Compress
'''


def windows_backing_volume(distribution=None):
    distribution = distribution or os.environ.get('WSL_DISTRO_NAME')
    if not distribution:
        raise RuntimeError('WSL distro name unavailable; cannot identify the backing volume')
    exe = shutil.which('powershell.exe')
    if not exe:
        raise RuntimeError('Windows PowerShell unavailable; WSL host storage cannot be verified')
    encoded = base64.b64encode(HOST_QUERY.encode('utf-16le')).decode('ascii')
    proc = subprocess.run([exe, '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
                          capture_output=True, timeout=20, check=True)
    rows = json.loads(proc.stdout.decode('utf-8-sig'))
    if isinstance(rows, dict):
        rows = [rows]
    matches = [row for row in rows if row['distribution'] == distribution]
    if len(matches) != 1:
        raise RuntimeError('Could not unambiguously locate this WSL distribution')
    host = matches[0]
    if not isinstance(host['free_bytes'], int) or host['free_bytes'] < 0:
        raise RuntimeError('Invalid Windows free-space measurement')
    return host


def storage_snapshot(path):
    path = Path(path).resolve()
    local = shutil.disk_usage(path)
    result = {'path': str(path), 'filesystem_free_bytes': local.free,
              'filesystem_total_bytes': local.total, 'windows_backing_volume': None,
              'policy': 'Conservative growth budget; allocated but reusable VHDX blocks are not credited.'}
    if 'microsoft' in platform.release().lower():
        # Production roots are Linux paths on this distro. Do not silently
        # apply its backing-drive result to a different mounted Windows drive.
        if str(path).startswith('/mnt/'):
            raise RuntimeError('Mounted-drive output requires a separately reviewed storage mapping')
        result['windows_backing_volume'] = windows_backing_volume()
    capacities = [local.free]
    if result['windows_backing_volume']:
        capacities.append(result['windows_backing_volume']['free_bytes'])
    result['effective_free_bytes'] = min(capacities)
    return result


def require_storage(snapshot, required_bytes, safety_bytes=10*GIB):
    if required_bytes < 0 or safety_bytes < 0:
        raise ValueError('Negative storage budget')
    available = snapshot['effective_free_bytes']
    if available < required_bytes + safety_bytes:
        host = snapshot.get('windows_backing_volume')
        host_text = f"; Windows {host['drive']} {host['free_bytes']/GIB:.2f} GiB free" if host else ''
        raise RuntimeError(
            f"Insufficient raw-retention space: need {required_bytes/GIB:.2f} GiB plus "
            f"{safety_bytes/GIB:.2f} GiB safety reserve; effective free {available/GIB:.2f} GiB"
            f"{host_text}. Nothing launched or deleted.")
    return snapshot


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('path')
    p.add_argument('--required-gib', type=float, default=0)
    a = p.parse_args()
    snapshot = storage_snapshot(a.path)
    print(json.dumps(snapshot, indent=2), flush=True)
    require_storage(snapshot, int(a.required_gib*GIB))
