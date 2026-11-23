"""Posters of a complete run: the last saved state (t = 5 t_cc), edge on and face on.

Each poster is the last 128 pixel row of edge.png or face.png, scaled with Lanczos to 768 x 384 (edge on)
or 384 x 384 (face on) and saved as JPEG quality 92, with nothing drawn over it.

  python make_posters.py <folder with one subfolder per run> [run id ...]
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

root = Path(sys.argv[1])
ids = sys.argv[2:] or sorted(p.name for p in root.iterdir() if (p / 'entry.json').is_file())
for rid in ids:
    run = root / rid
    entry = json.loads((run / 'entry.json').read_text(encoding='utf-8'))
    n = len(entry['frames'])
    assert abs(entry['frames'][-1]['time'] - 5.0) < 0.01, rid
    for view, size in (('edge', (768, 384)), ('face', (384, 384))):
        sheet = np.asarray(Image.open(run / f'{view}.png').convert('RGB'))
        assert sheet.shape[0] == 128 * n, (rid, view, sheet.shape)
        poster = Image.fromarray(sheet[128 * (n - 1):]).resize(size, Image.Resampling.LANCZOS)
        out = run / f'poster-{view}.jpg'
        tmp = out.with_name('tmp-' + out.name)
        poster.save(tmp, quality=92)
        with Image.open(tmp) as check:
            check.load()
            assert check.size == size and check.mode == 'RGB'
        tmp.replace(out)
    print(rid, 'state', n - 1, 't =', round(entry['frames'][-1]['time'], 4))
