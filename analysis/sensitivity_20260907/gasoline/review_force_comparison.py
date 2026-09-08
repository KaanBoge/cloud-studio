"""Independent exact-rational spot checks of all claimed native order cases.

Does not import the force parser/comparator. Native data is read, never modified.
"""
from collections import Counter
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct

ROOT = Path('/home/kaan/sensitivity_20260907/gasoline')
INPUT = ROOT / 'force_order_compare_v1/report.json'
EXPECTED = '5c78fd85a3f5dc35800443a200955a883ecd97dce512b1bc7af665c48c66f7ef'
OUT = ROOT / 'force_order_review_v1'
FIELDS = ('a0', 'a1', 'a2', 'uDotPdV', 'uDotAV', 'uDotDiff')
SCHEMA = struct.Struct('<4Q8i8Q')
ORDER = 'observed_order_explains_this_selected_accumulator'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def double(bits):
    return struct.unpack('<d', struct.pack('<Q', bits))[0]


def packed(value):
    return struct.unpack('<Q', struct.pack('<d', value))[0]


def rational_sum(start, updates):
    current = double(start)
    for row in updates:
        if packed(current) != row[12]:
            raise ValueError('Independent continuity mismatch')
        other = double(row[13])
        if row[9] == 2:
            other = -other
        elif row[9] != 1:
            raise ValueError('Unknown selected operation')
        exact = Fraction.from_float(current) + Fraction.from_float(other)
        rounded = float(exact)
        if exact == 0 and current == 0 and other == 0:
            rounded = -0. if math.copysign(1., current) < 0 and math.copysign(1., other) < 0 else 0.
        if packed(rounded) != row[14]:
            raise ValueError('Exact rational sum rounded to binary64 disagrees')
        current = rounded
    return packed(current)


def main():
    if OUT.exists():
        raise FileExistsError('Independent review already attempted')
    if digest(INPUT) != EXPECTED:
        raise ValueError('Comparison evidence changed')
    source = json.loads(INPUT.read_text())
    traces = {}
    for name in ('off_a', 'off_b', 'on'):
        accumulators = {}
        for rank in (0, 1):
            path = ROOT / 'force_order_cases_v1' / name / ('force.rank%02d.bin' % rank)
            if digest(path) != source['input_pins'][str(path)]:
                raise ValueError('Native input trace changed')
            data = path.read_bytes()
            if data[:8] != b'CFTv1\0\0\0' or (len(data) - 8) % 128:
                raise ValueError('Independent trace schema mismatch')
            for row in SCHEMA.iter_unpack(data[8:]):
                if row[7] in (1, 7) or row[11] != 0:
                    continue
                key = (row[1], row[2], row[5], row[8])
                if row[7] == 2:
                    if key in accumulators:
                        raise ValueError('Independent duplicate owner')
                    accumulators[key] = dict(initial=row[14], updates=[], final=None)
                elif row[7] == 3:
                    accumulators[key]['initial'] = row[14]
                elif row[7] in (4, 5):
                    accumulators[key]['updates'].append(row)
                elif row[7] == 6:
                    accumulators[key]['final'] = row[14]
        if len(accumulators) != 546:
            raise ValueError('Independent population mismatch')
        traces[name] = accumulators
    checks = []
    for pair in source['pairs']:
        records = pair['records']
        if len(records) != 546 or Counter(r['classification'] for r in records) != pair['classifications']:
            raise ValueError('Reported classification totals disagree')
        if sum(r['endpoint_bits_differ'] for r in records) != pair['endpoint_differences']:
            raise ValueError('Reported endpoint totals disagree')
        for r in records:
            if r['classification'] != ORDER:
                continue
            key = (r['phase'], int(r['time_bits'], 16), r['target'], FIELDS.index(r['component']))
            a, b = [traces[n][key] for n in pair['cases']]
            token = lambda x: (x[7], x[9], x[13], x[6], x[18], x[15], x[16], x[17], x[10])
            ta, tb = [[token(x) for x in g['updates']] for g in (a, b)]
            if a['initial'] != b['initial'] or Counter(ta) != Counter(tb) or ta == tb:
                raise ValueError('Independent strict contribution test failed')
            ends = [rational_sum(g['initial'], g['updates']) for g in (a, b)]
            if ends != [a['final'], b['final']] or ends[0] == ends[1]:
                raise ValueError('Independent endpoint test failed')
            if ends != [int(x, 16) for x in r['endpoint_bits']]:
                raise ValueError('Compared report endpoint changed')
            checks.append(dict(cases=pair['cases'], phase=r['phase'], time_code=r['time_code'],
                               target=r['target'], component=r['component'],
                               strict_multiset_equal=True, rational_replay_exact=True))
    OUT.mkdir()
    shutil.copy2(__file__, OUT / Path(__file__).name)
    result = dict(status='passed_independent_selected_order_checks',
                  comparison_sha256=EXPECTED, source_sha256=digest(__file__),
                  paired_summary_counts_checked=1638, order_comparisons_checked=len(checks),
                  exact_rational_owner_sums_checked=2 * len(checks), checks=checks,
                  method='Independent struct reader; exact rational add/sub rounded to binary64 at each native event.',
                  scope='All claimed order-only pairs, not an independent classification of every changed-input case.',
                  old_field_gate_still_failed=True, native_runs_launched=0)
    with (OUT / 'report.json').open('x') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'checks'}, indent=2))


if __name__ == '__main__':
    main()
