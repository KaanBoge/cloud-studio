"""Read-only comparison of completed, pinned native force traces (8 Sep 2026).

This never launches a solver or changes a trajectory acceptance threshold.
Original native validation is reused by hash; owner sums are compared separately
after the actual native initializer, retaining pre-initialization values too.
"""
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

import force_trace_replay as f

ROOT = Path('/home/kaan/sensitivity_20260907/gasoline')
RUNNER = ROOT / 'force_order_runner_v1'
OUT = ROOT / 'force_order_compare_v1'
REPORT_SHA = '94ed097aa774b930c065bb1710d2c4f4f9d4cf618adcf09c52b23debf8822b97'
REPLAY_SHA = '4d5a510dd2cc3332620523696fcaf471f3fb80072e121a8bd7c5b94a414642ee'
NAMES = ('off_a', 'off_b', 'on')
COMPONENTS = ('a0', 'a1', 'a2', 'uDotPdV', 'uDotAV', 'uDotDiff')
ORDER = 'observed_order_explains_this_selected_accumulator'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with Path(path).open('x', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')


def hx(value):
    return '0x%016x' % value


def group_owners(streams):
    """Use already validated records; reject new grouping/reset ambiguities."""
    groups = {}
    for stream in streams:
        for r in stream:
            if r.kind in (f.BEGIN, f.END) or r.role != f.OWNER:
                continue
            key = (r.phase, r.time_bits, r.target, r.component)
            if r.kind == f.BASELINE:
                if key in groups:
                    raise ValueError('Duplicate owner identity across streams')
                groups[key] = dict(rank=r.rank, baseline=r.before, initial=r.after,
                                   resets=[], events=[], final=None,
                                   baseline_sequence=r.sequence, final_sequence=None)
                continue
            if key not in groups:
                raise ValueError('Owner event without baseline')
            g = groups[key]
            if g['rank'] != r.rank or g['final'] is not None:
                raise ValueError('Owner changed rank or event follows final')
            if r.kind == f.RESET:
                if g['events'] or g['resets'] or r.component < 3:
                    raise ValueError('Unexpected repeated, late or acceleration reset')
                g['resets'].append(r)
                g['initial'] = r.after
            elif r.kind in (f.LOCAL, f.REMOTE):
                g['events'].append(r)
            elif r.kind == f.FINAL:
                g['final'] = r.after
                g['final_sequence'] = r.sequence
            else:
                raise ValueError('Unrecognized owner event')
    if not groups or any(g['final'] is None for g in groups.values()):
        raise ValueError('Missing owner final')
    for g in groups.values():
        if f.replay_terms(g['initial'], terms(g)) != g['final']:
            raise ValueError('Grouped native sum does not replay exactly')
    return groups


def terms(g):
    return [(r.operation, r.operand) for r in g['events']]


def tokens(g):
    # No inferred sender rank: REMOTE partner is the recorded callback particle ID.
    return [(r.kind, r.operation, r.operand, r.partner, r.arity,
             r.arg0, r.arg1, r.arg2, r.active) for r in g['events']]


def classify(a, b):
    # Verify both sums even if a later input-population test fails.
    numeric = f.compare_orders(a['initial'], terms(a), a['final'],
                               b['initial'], terms(b), b['final'])
    if a['initial'] != b['initial']:
        return 'different_starting_values'
    if Counter(tokens(a)) != Counter(tokens(b)):
        return 'different_contribution_population_or_values'
    return numeric


def event_record(r):
    result = r._asdict()
    for name in ('time_bits', 'before', 'operand', 'after', 'arg0', 'arg1', 'arg2'):
        result[name] = hx(result[name])
    result['trace_byte_offset'] = len(f.MAGIC) + (r.sequence - 1) * f.RECORD.size
    return result


def detail(g):
    return dict(rank=g['rank'], baseline=hx(g['baseline']), initial=hx(g['initial']),
                final=hx(g['final']), baseline_sequence=g['baseline_sequence'],
                final_sequence=g['final_sequence'],
                resets=[event_record(r) for r in g['resets']],
                events=[event_record(r) for r in g['events']])


def compare_pair(name_a, aa, name_b, bb):
    if set(aa) != set(bb):
        raise ValueError('Owner phase/time/ID/component populations differ')
    records = []
    counts = Counter()
    different_counts = Counter()
    examples = {}
    first_different = None
    maxima = dict.fromkeys(COMPONENTS, 0.)
    for key in sorted(aa, key=lambda k: (f.number(k[1]), k[0], k[2], k[3])):
        a, b = aa[key], bb[key]
        category = classify(a, b)
        different = a['final'] != b['final']
        magnitude = abs(f.number(a['final']) - f.number(b['final']))
        counts[category] += 1
        if different:
            different_counts[category] += 1
        component = COMPONENTS[key[3]]
        maxima[component] = max(maxima[component], magnitude)
        record = dict(phase=key[0], time_code=f.number(key[1]), time_bits=hx(key[1]),
                      target=key[2], component=component, classification=category,
                      endpoint_bits_differ=different, absolute_endpoint_difference=magnitude,
                      owner_ranks=[a['rank'], b['rank']],
                      pre_init_baselines=[hx(a['baseline']), hx(b['baseline'])],
                      post_init_starts=[hx(a['initial']), hx(b['initial'])],
                      reset_counts=[len(a['resets']), len(b['resets'])],
                      endpoint_bits=[hx(a['final']), hx(b['final'])],
                      contribution_counts=[len(a['events']), len(b['events'])],
                      same_numeric_multiset=Counter(terms(a)) == Counter(terms(b)),
                      same_provenance_multiset=Counter(tokens(a)) == Counter(tokens(b)),
                      same_provenance_order=tokens(a) == tokens(b))
        records.append(record)
        if different and first_different is None:
            first_different = dict(summary=record, cases={name_a: detail(a), name_b: detail(b)})
        if different and len(examples.setdefault(category, [])) < 3:
            examples[category].append(dict(summary=record, cases={name_a: detail(a), name_b: detail(b)}))
    return dict(cases=[name_a, name_b], owner_accumulators=len(records),
                classifications=dict(counts), endpoint_differences=sum(different_counts.values()),
                endpoint_difference_classifications=dict(different_counts),
                max_absolute_endpoint_difference_by_component=maxima,
                first_endpoint_difference=first_different,
                first_three_different_examples_per_category=examples, records=records)


def main():
    if OUT.exists():
        raise FileExistsError('Read-only comparison stage already exists; do not overwrite')
    report_path = RUNNER / 'report.json'
    if sha(report_path) != REPORT_SHA or sha(Path(f.__file__)) != REPLAY_SHA:
        raise ValueError('Completed native report or replay source changed')
    report = json.loads(report_path.read_text())
    if report['status'] != 'three_native_force_traces_recorded_and_replayed':
        raise ValueError('Native stage not completed')
    if tuple(c['name'] for c in report['cases']) != NAMES:
        raise ValueError('Not all three planned native cases')
    pins = {str(report_path): REPORT_SHA, str(Path(f.__file__)): REPLAY_SHA}
    for c in report['cases']:
        expected = {str(ROOT / 'force_order_cases_v1' / c['name'] / ('force.rank%02d.bin' % r))
                    for r in (0, 1)}
        if set(c['trace']['files']) != expected:
            raise ValueError('Unexpected rank trace files')
        pins.update(c['trace']['files'])
    for path, value in pins.items():
        if sha(path) != value:
            raise ValueError('Completed evidence changed: ' + path)
    OUT.mkdir()
    for name in ('compare_force_order.py', 'test_compare_force_order.py',
                 'FORCE_COMPARISON_PLAN.md'):
        shutil.copy2(Path(__file__).parent / name, OUT / name)
    shutil.copy2(Path(f.__file__), OUT / 'force_trace_replay.py')
    save(OUT / 'plan.json', dict(status='frozen_read_only_comparison', input_pins=pins,
        source_pins={x.name: sha(x) for x in OUT.iterdir() if x.is_file()},
        native_runs_to_launch=0, criteria='FORCE_COMPARISON_PLAN.md'))
    start = time.monotonic()
    try:
        with (OUT / 'comparison_tests.log').open('x') as log:
            subprocess.run([sys.executable, '-m', 'unittest', '-v',
                            'test_compare_force_order.py'], cwd=OUT,
                           stdout=log, stderr=subprocess.STDOUT, check=True, timeout=30)
        groups = {}
        for c in report['cases']:
            paths = sorted(c['trace']['files'])
            groups[c['name']] = group_owners([f.rows(Path(p).read_bytes()) for p in paths])
            # Exact independently predeclared population; no dropping or interpolation.
            phases = {(k[0], k[1]) for k in groups[c['name']]}
            if {p for p, _ in phases} != set(range(1, 14)) or len(phases) != 13:
                raise ValueError('Unexpected native phase population')
            expected = {(p, t, target, comp) for p, t in phases
                        for target in f.TARGETS for comp in range(6)}
            if set(groups[c['name']]) != expected:
                raise ValueError('Missing selected owner/component')
        pairs = [compare_pair(a, groups[a], b, groups[b]) for a, b in itertools.combinations(NAMES, 2)]
        for path, value in pins.items():
            if sha(path) != value:
                raise ValueError('Completed evidence changed during analysis: ' + path)
        result = dict(status='completed_read_only_selected_force_order_comparison',
            native_report_sha256=REPORT_SHA, input_pins=pins,
            plan_sha256=sha(OUT / 'plan.json'), analysis_wall_seconds=time.monotonic() - start,
            pairs=pairs, selected_ids=list(f.TARGETS), phases=13, fields=list(COMPONENTS),
            accumulators_per_case=546, paired_accumulators=1638,
            native_runs_launched=0, new_native_states=0, accepted_full_controls=46,
            old_field_gate_still_failed=True, full_gasoline_controls_enabled=False,
            limits=['Selected force sums only, not a velocity-kick or trajectory proof.',
                    'Matching tokens record native subtotals, not complete remote-neighbor provenance.',
                    'Pre-initialization baseline differences are preserved even when reset clears them.',
                    'All cases use the trace build: observer effects and historical causality remain unproven.',
                    'No science threshold is relaxed and no completed native test is rerun.'])
        save(OUT / 'report.json', result)
        print(json.dumps(dict(status=result['status'], paired_accumulators=1638,
            pairs=[{k: p[k] for k in ('cases', 'classifications', 'endpoint_differences',
                   'endpoint_difference_classifications')} for p in pairs]), indent=2))
    except Exception as exc:
        save(OUT / 'failure.json', dict(error=repr(exc), native_runs_launched=0))
        raise


if __name__ == '__main__':
    main()
