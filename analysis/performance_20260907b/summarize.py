"""Report successes and rejected candidates; promote only validated GPU output encoding."""
import copy
import json
from pathlib import Path
from statistics import median
HERE=Path(__file__).resolve().parent
ROOT=Path('/home/kaan/performance_20260907b')
FIRST=HERE.parent/'performance_20260907'
rows={p.parent.name:json.loads(p.read_text()) for p in (ROOT/'runs').glob('*/result.json')}
fields=json.loads((HERE/'field_regression.json').read_text())
def compare(base,candidate):
    b=[rows[n]['wall_seconds'] for n in base];c=[rows[n]['wall_seconds'] for n in candidate]
    return dict(baseline_cases=base,candidate_cases=candidate,baseline_seconds=b,candidate_seconds=c,
        baseline_median=median(b),candidate_median=median(c),reduction_percent=100*(1-median(c)/median(b)))
report=dict(scope='Second-round tests at chi=100, Mach 2; speedups are relative to the already optimized profiles, not original stock binaries.',
    cpu_L5=compare(['current','current_repeat2','current_repeat3'],['lto128','best_repeat2','best_repeat3']),
    cpu_L6=compare(['L6_current'],['L6_candidate']),
    gpu_L6=compare(['gpu_io_c5','gpu_c5_repeat2','gpu_c5_repeat3'],['gpu_io_c1','gpu_c1_repeat2','gpu_c1_repeat3']),
    decisions={'CPU_L5':'Use LTO and 128x64x32 work blocks only after successful full native IC tests for all chi.',
      'CPU_L6':'Keep previous native-build/cubic-block profile: LTO/wide blocks were slower at L6.',
      'GPU_L6':'Use lossless compression level 1 for prim snapshots; retain checkpoint settings and every variable/time.',
      'GPU_compression_0':'Not selected: it used much more disk space. Native values were unchanged.',
      'universal_quality':'No universally faster-and-more-accurate setting has been established. No new accuracy/convergence claim.'},
    field_regression=fields,all_timings=rows)
report['gpu_L6']['container_size_ratio_c1_over_c5']=rows['gpu_io_c1']['native_bytes']/rows['gpu_io_c5']['native_bytes']
report['gpu_L6']['container_size_ratio_c0_over_c5']=rows['gpu_io_c0']['native_bytes']/rows['gpu_io_c5']['native_bytes']
(HERE/'performance_report.json').write_text(json.dumps(report,indent=2))
profile_path=FIRST/'optimized_profiles.json'
profiles=json.loads(profile_path.read_text())
prior=HERE/'profiles_before_io_change.json'
if not prior.exists():prior.write_text(json.dumps(profiles,indent=2))
proof=next(x for x in fields if x['candidate']=='gpu_io_c1')
assert all(x['passed'] for x in fields)
assert report['gpu_L6']['reduction_percent']>0
profiles['apk_L6'].update(hdf5_compression_level=1,directory_prefix='OPTIO1',io_regression=proof,
    io_scope='Prim snapshots only; restart settings unchanged',io_timing=report['gpu_L6'])
cpu=rows['lto128']
ics=json.loads((HERE/'lto_ic_results.json').read_text())
assert len(ics)==3 and all(r['passed'] and r['binary_sha256']==cpu['binary_sha256'] for r in ics)
profiles['athpp_L5'].update(binary=cpu['binary'],binary_sha256=cpu['binary_sha256'],block=cpu['block'],
    benchmark_case='lto128',ic_proof_root=str(ROOT/'ic_tests'),directory_prefix='OPTLTO',
    regression=next(x for x in fields if x['candidate']=='lto128'),second_round_timing=report['cpu_L5'])
profile_path.write_text(json.dumps(profiles,indent=2))
for name in ('cpu_L5','cpu_L6','gpu_L6'):print(name,json.dumps(report[name]),flush=True)
