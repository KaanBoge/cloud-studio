"""Build reproducible benchmark summaries; failed/contended probes stay visible."""
import hashlib
import json
from pathlib import Path
import statistics

here=Path(__file__).resolve().parent
root=Path('/home/kaan/performance_20260907')
bench=root/'benchmarks_v3'
rows={f.parent.name:json.loads(f.read_text()) for f in bench.glob('*/result.json')}
reg=json.loads((here/'field_regression.json').read_text())

def summary(base,candidate):
    a=[rows[n]['wall_seconds_with_initialization_and_output'] for n in base]
    b=[rows[n]['wall_seconds_with_initialization_and_output'] for n in candidate]
    am,bm=statistics.median(a),statistics.median(b)
    return dict(baseline_cases=base,candidate_cases=candidate,baseline_seconds=a,candidate_seconds=b,
                median_baseline=am,median_candidate=bm,time_reduction_percent=100*(1-bm/am),speedup=am/bm)

report={'scope':'Short, early-time chi=100 Mach-2 3D tests on this PC. Not full-run timing or convergence proof.',
 'cpu_L5':summary(['base32_r8','base32_r8_repeat2','base32_r8_repeat3'],['native64_r16','best_repeat2','best_repeat3']),
 'cpu_L6':summary(['L6_cpu_base'],['L6_cpu_native']),
 'gpu_L5':summary(['apk_block32','apk_block32_repeat2','apk_block32_repeat3'],['apk_block64','apk_block64_repeat2','apk_block64_repeat3']),
 'gpu_L6':summary(['L6_apk_block64_retry'],['L6_apk_block128_clean']),
 'field_regression':reg,
 'excluded_or_failed':{'benchmarks_and_benchmarks_v2':'Cycle-limited/missing final output or interrupted attempts; not field/timing evidence.',
  'native64_r8':'MPI PMIx listener initialization failure. Independent retry succeeded.',
  'L6_apk_block32':'Initialization stalled; terminated after 300 seconds; no native output.',
  'L6_apk_block32_retry':'Initialization stalled near VRAM capacity; terminated after 120 seconds. Another probe overlapped its final ~35 seconds; no output was produced before overlap either.',
  'apk_block128':'Accidental overlap with the stalled block32 probe; timing excluded. Clean replacement retained.',
  'L6_apk_block128':'Stopped when overlap detected; excluded. Clean replacement retained.'},
 'all_result_records':rows}
(here/'performance_report.json').write_text(json.dumps(report,indent=2))
profiles={}
for code,level,case,base in [('athpp',5,'native64_r16','base32_r8'),('athpp',6,'L6_cpu_native','L6_cpu_base'),
 ('apk',5,'apk_block64','apk_block32'),('apk',6,'L6_apk_block128_clean','L6_apk_block64_retry')]:
    d=rows[case]
    proof=next(r for r in reg if r['baseline']==base and r['candidate']==case)
    assert proof['passed'] and d['returncode']==0
    # Actual output bytes are recorded separately from conservative launch reservations.
    n=8*2**level*(4*2**level)**2
    bpc=max(Path(f).stat().st_size for f in d['native_outputs'])/n
    profiles[f'{code}_L{level}']={
       'code':code,'level':level,'binary':d['binary'],'binary_sha256':d['binary_sha256'],
       'ranks':d['ranks'],'block':d['block'],'benchmark_case':case,'regression':proof,
       'measured_native_output_bytes_per_cell':bpc,
       'ic_proof_root':str(root/'ic_tests' if code=='athpp' else Path('/home/kaan/ic_audit_20260907/grid_tests')),
       'production_validation':'pending; short tests are not a completed replacement run'}
(here/'optimized_profiles.json').write_text(json.dumps(profiles,indent=2))
for k in ('cpu_L5','cpu_L6','gpu_L5','gpu_L6'):
    print(k,report[k]['median_baseline'],report[k]['median_candidate'],report[k]['time_reduction_percent'])
