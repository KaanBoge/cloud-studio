"""Add the n = 128 dense mass histories of seven methods to plot_series.json.

Each history is the saved reduction of one calculation: times in cloud crushing times
and the dense mass divided by its initial value. The reductions were validated by
reproducing the n = 32 and n = 64 histories of the same code already in plot_series.json.

  python add_n128_series.py <folder holding the reductions>
"""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parent
A = Path(sys.argv[1])


def from_paper_format(path, code):
    rows = json.loads((A / path).read_text())
    row = next(r for r in rows if r['code'] == code and r['level'] == 5)
    return row['times'], row['dense']


def arepo():
    d = json.loads((A / 'arepo/series.json').read_text())['runs']['L5']
    return d['t_over_tcc'], d['f_dense']


def gadget4():
    d = json.loads((A / 'gadget4/series.json').read_text())['levels']['L5']
    return d['time_tcc'], d['f_d']


new = {
    'apk': ('n128_athena/level5_for_paper.json', lambda: from_paper_format('n128_athena/level5_for_paper.json', 'apk')),
    'athw': ('n128_athena/level5_for_paper.json', lambda: from_paper_format('n128_athena/level5_for_paper.json', 'athw')),
    'ramses': ('n128_ramses/level5_for_paper.json', lambda: from_paper_format('n128_ramses/level5_for_paper.json', 'ramses')),
    'flash': ('n128_flash/level5_for_paper.json', lambda: from_paper_format('n128_flash/level5_for_paper.json', 'flash')),
    'flashx': ('n128_flash/level5_for_paper.json', lambda: from_paper_format('n128_flash/level5_for_paper.json', 'flashx')),
    'arepo': ('arepo/series.json', arepo),
    'gadget4': ('gadget4/series.json', gadget4),
}

path = ROOT / 'plot_series.json'
rows = json.loads(path.read_text())
have = {(r['code'], r['level']) for r in rows}
added = []
for code, (source, load) in new.items():
    if (code, 5) in have:
        continue
    times, dense = load()
    assert len(times) == len(dense) == 101, (code, len(times), len(dense))
    assert times[0] == 0.0 and abs(dense[0] - 1.0) < 1e-12 and 4.99 < times[-1] < 5.01, code
    assert all(b > a for a, b in zip(times, times[1:])), code
    rows.append({'code': code, 'level': 5, 'times': list(times), 'dense': list(dense),
                 'source': 'reductions_20261122/' + source,
                 'sha256': hashlib.sha256((A / source).read_bytes()).hexdigest()})
    added.append(code)
path.write_text(json.dumps(rows))
print('added', added, 'rows now', len(rows))
