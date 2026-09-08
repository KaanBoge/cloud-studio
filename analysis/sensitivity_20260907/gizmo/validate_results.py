"""Pre-publication read-only checks for the completed MFM pair and MFV audit."""
import fcntl,json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,'/home/kaan/sensitivity_20260907/gizmo/runner_l3_v1')
from run_full_l3 import ROOT,sha,save,check_times
from verify_gizmo import native,sums
from audit_mfv_pair import resource_summary

def main():
    locks=[]
    for name in ('benchmark.lock','production.lock'):
        handle=Path('/home/kaan/performance_20260907',name).open('a')
        fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(handle)
    dest=ROOT/'delivery_validation.json'
    if dest.exists():raise ValueError('Completed delivery validation exists; do not overwrite')
    report_path=ROOT/'analysis_mfm_l3'/'report.json'
    r=json.loads(report_path.read_text());batch=json.loads((ROOT/'full_l3_batch.json').read_text())
    if r['batch_sha256']!=sha(ROOT/'full_l3_batch.json'):raise ValueError('Batch differs')
    script=Path(__file__).parent/'analyze_mfm_l3.py'
    if r['analysis_sha256']!=sha(script):raise ValueError('Analysis script differs')
    cases=sorted(batch['finished'],key=lambda c:c['mode'])
    if [(c['variant'],c['mode'],c['status']) for c in cases]!=[('mfm',0,'complete_independent_checks'),('mfm',1,'complete_independent_checks')]:
        raise ValueError('Unexpected accepted controls')
    curves=[];resources=[];native_count=0;largest=0.0
    for c in cases:
        rows=r['series'][str(c['mode'])];check_times([x['time_code'] for x in rows],c['physics'])
        if rows!=c['series']:raise ValueError('Report and native ledger differ')
        denominator=rows[0]['dense_mass']
        if denominator<=0 or denominator!=cases[0]['series'][0]['dense_mass']:raise ValueError('Unmatched denominator')
        for row in rows:
            path=Path(row['snapshot']);digest=sha(path)
            if digest!=row['sha256']:raise ValueError('Snapshot differs')
            arrays,t=native(path,c['physics'],'mfm');measured=sums(arrays,c['physics'])
            if t!=row['time_code'] or len(arrays['Masses'])!=row['elements']:raise ValueError('Time/count differs')
            for name,value in measured.items():
                delta=abs(value-row[name])/max(abs(value),1e-12);largest=max(largest,delta)
                if delta>1e-12:raise ValueError('Mass value differs')
            if row['dense_mass_over_initial']!=measured['dense_mass']/denominator:raise ValueError('Normalization differs')
            if max(row['independent_relative_errors'].values())>1e-11 or sha(path)!=digest:raise ValueError('Independent check/hash differs')
            native_count+=1
        curves.append(np.interp(np.linspace(0,5,101),[x['t_over_tcc'] for x in rows],[x['dense_mass_over_initial'] for x in rows]))
        resources.append(dict(mode=c['mode'],**resource_summary(Path(c['directory']))))
    peak=float(np.max(abs(curves[0]-curves[1])))
    if peak!=r['peak_curve_difference_over_initial_mass'] or native_count!=202:raise ValueError('Metric/count differs')
    audit=json.loads((ROOT/'mfv_pair_audit.json').read_text())
    if audit['original_batch_sha256']!=sha(ROOT/'full_l3_batch.json') or audit['script_sha256']!=sha(Path(__file__).parent/'audit_mfv_pair.py'):
        raise ValueError('MFV diagnostic provenance differs')
    if any(c['bad_fields']!=['InternalEnergy'] or c['cadence']['native_snapshots']!=101 for c in audit['cases']):raise ValueError('Unexpected failure scope')
    result=dict(status='share_mfm_with_caveats_mfv_not_certified',mfm_accepted_controls=2,mfm_native_states_rechecked=native_count,
        mfm_report_sha256=sha(report_path),mfm_plot_sha256=sha(ROOT/'analysis_mfm_l3'/'mass_mfm_L3.png'),
        batch_sha256=sha(ROOT/'full_l3_batch.json'),mfv_audit_sha256=sha(ROOT/'mfv_pair_audit.json'),
        mfv_failed_controls=2,mfv_native_states_audited=202,largest_direct_mass_recheck_relative_difference=largest,
        peak_curve_difference_over_initial_mass=peak,resources=resources,script_sha256=sha(__file__),
        method='Fresh direct native sums and raw-file hashes; existing per-state independent yt evidence verified in the immutable batch. Scalar peak recomputed with fixed initial denominator. This is not a new solver run or a rerun of the completed analyzer.')
    save(dest,result);print(json.dumps(result,indent=2))

if __name__=='__main__':main()
