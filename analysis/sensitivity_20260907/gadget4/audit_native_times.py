"""Verify existing native headers against the unchanged native output scheduler."""
import json,sys
from pathlib import Path
import h5py,numpy as np
sys.path.insert(0,'/home/kaan/sensitivity_20260907/gadget4')
from gadget_controls import ROOT,dependencies,sha,save,parameters,metadata
from native_cadence import cadence,expected_times

def main():
    dest=ROOT/'native_cadence_audit.json'
    if dest.exists():raise ValueError('Existing time audit must not be overwritten')
    dependencies();source=(ROOT/'native_run.cc').read_text();config=(ROOT/'native_config.h').read_text();constants=(ROOT/'native_constants.h').read_text()
    if 'ENLARGE_DYNAMIC_RANGE_IN_TIME' in config or 'OUTPUT_NON_SYNCHRONIZED_ALLOWED' in config or '#define TIMEBINS 29' not in constants:raise ValueError('Wrong native compile-time scheduler')
    for fragment in ('ti = ((integertime)(multiplier + 0.5)) * timax;','timax = ti_min;','time += All.TimeBetSnapshot;'):
        if fragment not in source:raise ValueError('Native scheduler source differs')
    folder=ROOT/'full_l3_v1/sharp13';values=parameters((folder/'params.txt').read_text());rows=[]
    for path in sorted((folder/'output').glob('snapshot_*.hdf5')):
        with h5py.File(path) as h:stamp=float(h['Header'].attrs['Time'])
        rows.append(dict(path=str(path),time_code=stamp,sha256=sha(path)))
    result=cadence([r['time_code'] for r in rows],metadata(),values);expected,unit,block=expected_times(values)
    requested=np.linspace(0,float(values['TimeMax']),101);deltas=np.array([r['time_code'] for r in rows])-requested
    report=dict(status='passed_exact_native_schedule',checks=result,native_run_source_sha256=sha(ROOT/'native_run.cc'),
        native_constants_sha256=sha(ROOT/'native_constants.h'),native_config_sha256=sha(ROOT/'native_config.h'),
        corrected_checker_sha256=sha(Path(__file__).with_name('native_cadence.py')),rows=rows,
        earliest_offset_code=float(deltas.min()),latest_offset_code=float(deltas.max()),
        cause='Original custom validator incorrectly required late-only snapshots. Native run.cc explicitly rounds to nearest available power-of-two time block, possibly early or late. Reconstructed schedule matches every header; no native field/time/run changed.')
    save(dest,report);print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))

if __name__=='__main__':main()
