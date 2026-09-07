"""Non-production regression suite and read-only machine budget audit."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path('/mnt/c/Users/kaanb/CloudCrushing')
WORK=Path('/home/kaan/followup_20260907')
sys.path[:0]=['/home/kaan/verified_20260907','/home/kaan/performance_20260907']
from storage_guard import storage_snapshot,require_storage,GIB
from run_optimized import budgets


def main():
    env=dict(os.environ,PYTHONPATH='/home/kaan/verified_20260907:/home/kaan/performance_20260907')
    result={'scope':'regressions and preflight only; no production launch','suites':[]}
    for folder,pattern in [('followup_20260907','test_storage_guard.py'),('followup_20260907','test_comparison_checks.py'),
                           ('followup_20260907','test_cooling_guard.py'),('audit_20260907','test_analysis.py'),
                           ('audit_20260907','test_additional.py'),('performance_20260907','test_optimized.py')]:
        cmd=[sys.executable,'-m','unittest','discover','-s',str(ROOT/folder),'-p',pattern,'-v']
        r=subprocess.run(cmd,env=env,capture_output=True,text=True)
        record={'test':pattern,'returncode':r.returncode,'log':r.stdout+r.stderr}
        result['suites'].append(record);print(pattern,r.returncode,flush=True)
        if r.returncode:raise RuntimeError(record)
    for name in ('week_queue.sh','gal_queue.sh'):
        r=subprocess.run(['bash','/home/kaan/'+name],capture_output=True,text=True)
        if r.returncode!=78:raise RuntimeError('Legacy queue guard did not refuse')
        result[name]={'returncode':r.returncode,'message':r.stdout+r.stderr}
    disk=storage_snapshot('/home/kaan');result['storage']=disk
    # Use a representative conservative size; this does not execute any launcher.
    result['large_run_preflight']={}
    for level in (5,6):
        need,_=budgets({'level':level,'code':'athpp','measured_native_output_bytes_per_cell':48.1})
        try:require_storage(disk,need)
        except (RuntimeError,ValueError) as e:status=str(e)
        else:status='fits conservative storage budget only; not science approval'
        result['large_run_preflight'][str(level)]={'required_gib':need/GIB,'status':status}
    result['passed']=True
    (WORK/'evidence/regression_suite.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='suites'},indent=2))

if __name__=='__main__':main()
