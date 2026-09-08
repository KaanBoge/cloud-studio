"""Summarize the preserved failed test; never change its acceptance criterion.

Machine-specific read-only verification of native files. Only a NEW review JSON
is written. No simulation, source edit, deletion, rerun or timestamp change.
"""
import hashlib
import json
import math
from pathlib import Path
import shutil
import statistics

ROOT = Path('/home/kaan/sensitivity_20260907/gasoline')
AUDIT = ROOT / 'longer_2rank_audit_v1/report.json'
OUTPUT = ROOT / 'longer_2rank_review_v1.json'
AUDIT_SHA = '3329dc075b9873cd608aa7a0ff9533ed4215c65145cc573c92190b3a23d544ff'
GIB = 1024**3


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def summarize(report):
    rows = report['comparisons']
    if len(rows) != 120 or len(report['states']) != 81:
        raise ValueError('Incomplete four-case, twenty-evolved-state comparison')
    pairs = {}
    for row in rows:
        key = (row['first'], row['second'])
        pairs.setdefault(key, []).append(row)
    if len(pairs) != 6 or any(len(x) != 20 for x in pairs.values()):
        raise ValueError('Missing comparison pair')
    summaries = []
    for (first, second), group in pairs.items():
        summaries.append(dict(first=first, second=second, comparisons=20,
            failed_states=[x['snapshot'] for x in group if not x['passed']],
            dense_membership_exact=all(x['dense_membership_exact'] for x in group),
            required_exact_fields=all(all(x['required_exact_fields'].values()) for x in group),
            field_maxima={k:dict(
                max_spacing_ratio=max(x['finite_precision'][k]['max_spacing_ratio'] for x in group),
                max_absolute=max(x['finite_precision'][k]['max_absolute'] for x in group),
                failed_states=[x['snapshot'] for x in group if not x['finite_precision'][k]['passed']])
                for k in ('rho', 'temp', 'vel', 'pos')}))
    passed = all(x['passed'] for x in rows)
    if passed != report['finite_precision_comparisons_passed']:
        raise ValueError('Acceptance status inconsistent with individual checks')
    independent = max(v for x in report['states']
                      for v in x['independent']['relative_discrepancies'])
    return dict(original_status=report['status'], original_test_passed=passed,
                full_science_controls_completed=0, native_output_count=81,
                comparisons=120, failed_comparisons=sum(not x['passed'] for x in rows),
                all_dense_memberships_exact=all(x['dense_membership_exact'] for x in rows),
                max_independent_mass_discrepancy=independent,
                exact_bitwise_equivalence=report['bitwise_comparisons_passed'], pairs=summaries)


def busy_workers(samples):
    rates = [(b[2]-a[2])/(b[0]-a[0]) for a,b in zip(samples, samples[1:])
             if b[0]>a[0] and b[2]>=a[2] and a[1]>0 and b[1]>0]
    if not rates:
        raise ValueError('No usable CPU samples')
    return statistics.median(rates)


def full_budget(state_bytes, checkpoint_bytes, ic_bytes, reader_cache_bytes):
    # 101 expected states; three extra slots and two extra stop checkpoints.
    state_bound = max(8*1024**2, math.ceil((max(state_bytes)+reader_cache_bytes)*1.25))
    per_case = math.ceil((104*state_bound + 12*checkpoint_bytes + ic_bytes + 256*1024**2)*1.25)
    return dict(measured_native_state_min=min(state_bytes),
        measured_native_state_max=max(state_bytes), reader_cache_max_per_state=reader_cache_bytes,
        state_budget_bytes=state_bound, native_checkpoint_bytes=checkpoint_bytes,
        expected_checkpoint_generations=10, budgeted_checkpoint_generations=12,
        ic_bytes=ic_bytes, per_case_bytes=per_case, pair_bytes=2*per_case,
        independent_reserve_bytes=10*GIB,
        formula='104 states including all sidecars and reader-cache allowance, 12 checkpoints, IC, 256 MiB logs; 25% additional margin per case. Ten native checkpoints expected at steps60..600. No full runner enabled.')


def main():
    if OUTPUT.exists():
        raise FileExistsError('Existing review must not be overwritten')
    if sha(AUDIT) != AUDIT_SHA:
        raise ValueError('Preserved audit changed')
    report = json.loads(AUDIT.read_text())
    result = summarize(report)
    state_bytes = []
    cache_bytes = []
    expected_sides = {'.HI', '.HeI', '.HeII', '.iord', '.pres', '.SPHH'}
    for row in report['states']:
        path = Path(row['path'])
        if sha(path) != row['sha256']:
            raise ValueError('Raw state changed: '+str(path))
        sides = {p.name[len(path.name):]:p for p in path.parent.glob(path.name+'.*')}
        if set(sides) != expected_sides:
            raise ValueError('Unexpected or missing native sidecars: '+str(path))
        for side in sides.values():
            if sha(side) != row['sidecars'][side.name]['sha256']:
                raise ValueError('Sidecar changed: '+str(side))
        state_bytes.append(path.stat().st_size + sum(p.stat().st_size for p in sides.values()))
        cache_bytes.append(sum(p.stat().st_size for p in AUDIT.parent.glob(row['case']+'_'+path.name+'.*')))
    checkpoints = [c for case in report['cases'] for c in case['checkpoints']]
    if len(checkpoints) != 8:
        raise ValueError('Missing retained checkpoint')
    for cp in checkpoints:
        if sha(cp['path']) != cp['sha256'] or Path(cp['path']).stat().st_size != cp['bytes']:
            raise ValueError('Checkpoint changed')
        if cp['header']['valid'] != 1 or cp['header']['count'] != 65536:
            raise ValueError('Invalid checkpoint header')
    ic = ROOT/'longer_validation_2rank_v1/retained_on/ic.std'
    budget = full_budget(state_bytes, max(x['bytes'] for x in checkpoints), ic.stat().st_size, max(cache_bytes))
    free = {name:shutil.disk_usage(path).free for name,path in
            [('guest',ROOT),('windows_backing_volume',Path('/mnt/c'))]}
    budget['free_bytes_at_review'] = free
    budget['fits_current_storage_only'] = all(x >= budget['pair_bytes']+10*GIB for x in free.values())
    result.update(audit_sha256=AUDIT_SHA, checker_sha256=sha(Path(__file__)),
        raw_states_and_all_sidecar_hashes_rechecked=81, checkpoint_hashes_rechecked=8,
        resources=[dict(case=x['name'], solver_seconds=x['solver_seconds'],
            peak_child_rss_bytes=x['peak_child_rss_bytes'], ranks=x['ranks'], guard=x['guard'],
            median_busy_workers=busy_workers(x['samples_elapsed_rss_cpu'])) for x in report['cases']],
        full_L3_pair_storage_budget=budget,
        decision='No full Gasoline controls enabled. The predeclared field criterion failed, including original-binary repeats. Exact dense mass through1t_cc is a measured limited result, not full-trajectory equivalence.',
        source_review='smoothfcn.c density routines accumulate neighbor contributions with floating-point additions. Summation order is a plausible source of repeat variability, not an established causal diagnosis; no solver arithmetic was changed.')
    with OUTPUT.open('x') as f:
        json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
