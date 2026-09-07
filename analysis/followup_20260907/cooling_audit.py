"""Read-only forensic audit; never enables cooling or rewrites a historical run."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def inspect(path):
    path=Path(path)
    raw=path.read_text()
    values={}; section=''
    for line in raw.splitlines():
        line=line.split('#',1)[0].strip()
        if line.startswith('<') and line.endswith('>'):
            section=line[1:-1].lower()
        elif '=' in line:
            key,value=line.split('=',1)
            values[section+'/'+key.strip().lower()]=value.strip()
    logpath=path.parent/'run.out'
    log=logpath.read_text(errors='replace') if logpath.exists() else ''
    unused=('set but unused:' in log and 'cooling/integrator' in log and 'cooling/table_filename' in log)
    enable=values.get('cooling/enable_cooling','none').lower()
    temp=values.get('problem/cloud/t_wind_cgs')
    issues=[]
    if enable!='tabular':issues.append('tabular cooling is not enabled by the saved input')
    if unused:issues.append('native run log explicitly reports cooling integrator and table unused')
    table=values.get('cooling/table_filename','')
    if 'schure' in table.lower():issues.append('Schure table is not the requested Sutherland and Dopita table')
    if temp is not None and float(temp)<1:
        issues.append('wind temperature below 1 K is not a valid setup for this plasma cooling study')
    return dict(run_dir=str(path.parent),parameter_sha256=hashlib.sha256(raw.encode()).hexdigest(),
                saved_enable_cooling=enable,wind_temperature_kelvin=temp,table=table,
                native_log=str(logpath) if logpath.exists() else None,
                log_sha256=hashlib.sha256(log.encode()).hexdigest() if log else None,
                native_log_confirms_unused_cooling=unused,
                status='cooling_not_enabled' if unused and enable=='none' else 'requires_review',
                issues=issues,
                caveat='Saved inputs alone cannot exclude a runtime CLI override; the retained log is separate evidence.')


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();rows=[inspect(p) for p in sorted(a.root.glob('*cool*/athinput'))]
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps({'scope':'retained historical cooling-labelled inputs and logs','runs':rows},indent=2)+'\n')
    for r in rows:print(Path(r['run_dir']).name,r['status'],r['wind_temperature_kelvin'])
