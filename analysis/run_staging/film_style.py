"""Cloud Studio film renderer: the one film style for the two films of a complete run.

Every film of every complete run on Cloud Studio is drawn by this module, so that all films look the same.
Input is the picture of every saved state as a colour mapped image, which is exactly a sprite row of the run
(128 px high; 256 px wide edge on, 128 px wide face on; column density of all gas divided by initial cloud
density times cloud radius, logarithmic from 0.008 to 5, magma, +y up), the state times in t_cc and the label.
Output is film-edge.mp4 and film-face.mp4.

THE STYLE
  Format    1920 x 1080, H.264 High, yuv420p, BT.709 matrix and tags (limited range), 60 fps, crf 18; the crf is
            raised in steps of 2 only when a film would exceed 25 MB (25 000 000 bytes).
  Timing    the first state is held 0.5 s (30 frames); then simulation time runs linearly at 0.25 t_cc per second
            (240 frames per t_cc): state i is shown unblended on frame 30 + round((t_i - t_0) * 240) and the frames
            between two neighbouring states are linear cross fades of their two pictures; then the last state is
            held 1 s (60 more frames). 101 states from 0 to 5 t_cc give 30 + 1200 + 1 + 60 = 1291 frames.
  Picture   the sprite row scaled 6 times (1536 x 768 edge on, 768 x 768 face on), centred, top at y = 156, inside
            a 1 px frame line. Scaling is Lanczos; rows made of exact 2 x 2 blocks (levels 3 and 4, whose sprite
            rows repeat each cell) are scaled by repetition instead, so their cells stay sharp (upscale="auto").
  Text      one family, Segoe UI (Semibold for the label, Regular for everything else), drawn on the background
            outside the picture, so the cross fade never touches it and it stays sharp on every frame:
              top left   the label (exactly entry.json "label"), white, 42 px
                         "Mach 2 · edge on · wind from left to right" or "Mach 2 · face on · looking along the wind",
                         grey, 24 px
              top right  "t = 2.50 t" with a subscript "cc", amber #e5ba83 (the site accent), 44 px, two decimals,
                         the time interpolated linearly between the two neighbouring states, so it advances every frame
              bottom     a horizontal colour bar (the site's magma table), ticks 0.008, 0.1, 1 and 5, and the unit
                         "Σ / (ρc,0 R)" with "c,0" as a real subscript; "Cloud Studio" small, grey, bottom right
            Nothing else is written on the films.
  Colours   background #0b1017, text #ecf1f5, grey #9baab9, amber #e5ba83, frame line #26323f (the site's own).

USE FROM PYTHON (another staging tool)
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'film_style', '/mnt/d/CloudCrushing/run_simple/analysis_20261122/studio_impl/film_style/film_style.py')
    film_style = importlib.util.module_from_spec(spec); spec.loader.exec_module(film_style)
    films = film_style.render_films(edge_rows, face_rows, times, label, out_dir)

  edge_rows  uint8 array (n, 128, 256, 3), RGB: the sprite rows of edge.png state by state
             (edge_rows[i] is rows 128 i to 128 i + 127 of edge.png); a list of such images works too
  face_rows  uint8 array (n, 128, 128, 3), RGB: the sprite rows of face.png
  times      the n state times in t_cc, strictly increasing (entry.json "times")
  label      exactly entry.json "label"
  out_dir    folder that receives film-edge.mp4 and film-face.mp4; each film is written under a temporary name in
             tmp_dir (default out_dir), checked, then moved into place
  keywords   upscale="auto" | "lanczos" | "nearest", crf=18, tmp_dir=None, verify=True, check_state=50,
             reference_rows=None (dict edge=..., face=... to compare the decoded films with; default the input rows)
  returns    a dict for the "films" section of stage_report.json: renderer path and sha256, the style, the frame
             index of every state, and per view frames, bytes, sha256, crf, ffprobe fields, the full decode result
             and the check of the unblended frame of state 50 against the reference row scaled the same way.
  It needs numpy, Pillow, ffmpeg and ffprobe on the PATH and the Segoe UI fonts (Windows font folder, also seen
  from WSL as /mnt/c/Windows/Fonts). It runs one ffmpeg at a time next to the Python process.

COMMAND LINE (Ubuntu-D: /home/user/venv/bin/python film_style.py ...)
    film_style.py --id <id> --frames-from <kind>:<path> --label "<label>" --out <run folder> [--tmp <folder>]
  kinds  grid:<.npz>      cache of stage_grid.py (col_edge, col_face as float32 column density, times); the rows are
                          made with the same colour mapping and the same 128 px row geometry as stage_grid.py
         other:<.npz>     cache of stage_run2.py (rgb_e, rgb_f sprite rows, t_tcc)
         sprites:<folder> a staged run folder itself (edge.png, face.png, entry.json times)
  When the run folder holds entry.json, its label and times must equal the given label and the source times.
  When it holds edge.png and face.png, the source rows are compared with them pixel by pixel (reported), and the
  decoded films are checked against those sprite rows. When it holds stage_report.json, a "films" section is
  added to it (or replaced); nothing else in the report changes. --no-report leaves the report alone.
"""
import argparse, hashlib, json, math, os, re, shutil, subprocess, sys, time
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
FPS = 60
FRAMES_PER_TCC = 240                     # 0.25 t_cc per second of film
HOLD_START, HOLD_END = 30, 60            # 0.5 s before the timeline starts, 1 s after its last frame
SCALE = 6                                # 128 px sprite rows -> 768 px
PIC_TOP = 156
LEFT, RIGHT = 192, 1728                  # text aligned with the edge on picture
MAX_BYTES = 25 * 1000 * 1000
BG = (11, 16, 23); TEXT = (236, 241, 245); MUTED = (155, 170, 185); ACCENT = (229, 186, 131); LINE = (38, 50, 63)
SUBTITLE = {'edge': 'Mach 2 \u00b7 edge on \u00b7 wind from left to right', 'face': 'Mach 2 \u00b7 face on \u00b7 looking along the wind'}
ROW_SHAPE = {'edge': (128, 256, 3), 'face': (128, 128, 3)}
DASH = re.compile('[\u2012\u2013\u2014\u2015]|--| - ')

# The site's colour table (assets/recent/catalog.json "colormap", magma), as 8 bit RGB: round(255 * value).
LUT_HEX = (
    '00000401000501010601010802010902020b02020d03030f03031204041405041606051806051a07061c08071e090720'
    '0a08220b09240c09260d0a290e0b2b100b2d110c2f120d31130d34140e36150e38160f3b180f3d19103f1a10421c1044'
    '1d11471e114920114b21114e22115024125325125527125829115a2a115c2c115f2d11612f1163311165331067341069'
    '36106b38106c390f6e3b0f703d0f713f0f72400f74420f75440f764510774710784910784a10794c117a4e117b4f127b'
    '51127c52137c54137d56147d57157e59157e5a167e5c167f5d177f5f187f601880621980641a80651a80671b80681c81'
    '6a1c816b1d816d1d816e1e81701f81721f817320817521817621817822817922827b23827c23827e2482802582812581'
    '8326818426818627818827818928818b29818c29818e2a81902a81912b81932b80942c80962c80982d80992d809b2e7f'
    '9c2e7f9e2f7fa02f7fa1307ea3307ea5317ea6317da8327daa337dab337cad347cae347bb0357bb2357bb3367ab5367a'
    'b73779b83779ba3878bc3978bd3977bf3a77c03a76c23b75c43c75c53c74c73d73c83e73ca3e72cc3f71cd4071cf4070'
    'd0416fd2426fd3436ed5446dd6456cd8456cd9466bdb476adc4869de4968df4a68e04c67e24d66e34e65e44f64e55064'
    'e75263e85362e95462ea5661eb5760ec5860ed5a5fee5b5eef5d5ef05f5ef1605df2625df2645cf3655cf4675cf4695c'
    'f56b5cf66c5cf66e5cf7705cf7725cf8745cf8765cf9785df9795df97b5dfa7d5efa7f5efa815ffb835ffb8560fb8761'
    'fc8961fc8a62fc8c63fc8e64fc9065fd9266fd9467fd9668fd9869fd9a6afd9b6bfe9d6cfe9f6dfea16efea36ffea571'
    'fea772fea973feaa74feac76feae77feb078feb27afeb47bfeb67cfeb77efeb97ffebb81febd82febf84fec185fec287'
    'fec488fec68afec88cfeca8dfecc8ffecd90fecf92fed194fed395fed597fed799fed89afdda9cfddc9efddea0fde0a1'
    'fde2a3fde3a5fde5a7fde7a9fde9aafdebacfcecaefceeb0fcf0b2fcf2b4fcf4b6fcf6b8fcf7b9fcf9bbfcfbbdfcfdbf')
LUT8 = np.frombuffer(bytes.fromhex(LUT_HEX), dtype=np.uint8).reshape(256, 3)

_FONT_DIRS = ('/mnt/c/Windows/Fonts', 'C:/Windows/Fonts')
FONT_FILES = {'regular': 'segoeui.ttf', 'semibold': 'seguisb.ttf'}
_fonts = {}


def font(weight, size):
    key = (weight, size)
    if key not in _fonts:
        for d in _FONT_DIRS:
            p = os.path.join(d, FONT_FILES[weight])
            if os.path.exists(p):
                _fonts[key] = ImageFont.truetype(p, size); break
        else:
            raise FileNotFoundError('Segoe UI not found in ' + ', '.join(_FONT_DIRS))
    return _fonts[key]


def win_path(p):
    s = str(Path(p).resolve()).replace('\\', '/')
    return 'D:/' + s[len('/mnt/d/'):] if s.startswith('/mnt/d/') else s


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def not_zero_filled(p):
    """The PC has corrupted fresh files into zeros before: a written file must be non empty and must not hold a
    4 KiB page of zeros anywhere (neither an MP4 with H.264 nor a JSON file can hold one)."""
    with open(p, 'rb') as fh:
        data = fh.read()
    if not data: return False
    for off in range(0, len(data), 4096):
        b = data[off:off + 4096]
        if len(b) == 4096 and not any(b): return False
    return any(data[-4096:])


RENDERER = dict(path=win_path(__file__), sha256=sha256_file(__file__))


# ------------------------------------------------------------------ colour mapping (only for the grid cache adapter)
def color(x):
    """Column density -> sprite colours, the mapping of stage_grid.py and stage_run2.py: log10 from 0.008 to 5 onto the
    256 colours of the site table (index floor(255 * fraction)), rows flipped so +y is up."""
    idx = np.floor(np.clip((np.log10(np.maximum(x, 1e-30)) - np.log10(.008)) / (np.log10(5) - np.log10(.008)), 0, 1) * 255).astype(int)
    return LUT8[idx][::-1]


def to_sprite(col):
    """Native column density map (N x 2N or N x N) -> the 128 px row geometry, as stage_grid.py."""
    n = col.shape[0]
    if n == 128: return col
    if n < 128:
        f = 128 // n; return np.repeat(np.repeat(col, f, axis=0), f, axis=1)
    f = n // 128; h, w = col.shape
    return col.reshape(h // f, f, w // f, f).mean(axis=(1, 3))


# ------------------------------------------------------------------ layout
def picture_box(view):
    w, h = (256 * SCALE, 128 * SCALE) if view == 'edge' else (128 * SCALE, 128 * SCALE)
    return (W - w) // 2, PIC_TOP, w, h


def blocky(rows):
    """True when every row is made of exact 2 x 2 blocks (sprite rows of levels 3 and 4)."""
    return bool(np.array_equal(rows[:, 0::2], rows[:, 1::2]) and np.array_equal(rows[:, :, 0::2], rows[:, :, 1::2]))


def scale_picture(row, view, mode):
    x0, y0, w, h = picture_box(view)
    resample = Image.Resampling.NEAREST if mode == 'nearest' else Image.Resampling.LANCZOS
    return np.asarray(Image.fromarray(np.ascontiguousarray(row)).resize((w, h), resample), dtype=np.uint8)


def draw_sub(d, x, base, main, sub, f_main, f_sub, shift, fill):
    """Draw main text, then a real subscript after it; returns the x after the subscript."""
    d.text((x, base), main, font=f_main, fill=fill, anchor='ls')
    x += f_main.getlength(main) + 1
    d.text((x, base + shift), sub, font=f_sub, fill=fill, anchor='ls')
    return x + f_sub.getlength(sub)


class Readout:
    """'t = 2.50 t' with a subscript 'cc', top right, baseline 92; its left end is fixed (Segoe UI digits are tabular),
    so only the digits change from frame to frame."""
    BASE = 92

    def __init__(self, longest):
        self.fa = font('regular', 44); self.fs = font('regular', 28)
        assert len({round(self.fa.getlength(c), 3) for c in '0123456789'}) == 1, 'digits are not tabular'
        width = self.fa.getlength('t = %s t' % longest) + 1 + self.fs.getlength('cc')
        self.tx = int(math.floor(RIGHT - width))
        self.x0, self.x1 = self.tx - 8, RIGHT + 8
        self.y0, self.y1 = self.BASE - 62, self.BASE + 28
        self.cache = {}

    def patch(self, s):
        if s not in self.cache:
            img = Image.new('RGB', (self.x1 - self.x0, self.y1 - self.y0), BG); d = ImageDraw.Draw(img)
            draw_sub(d, self.tx - self.x0, self.BASE - self.y0, 't = %s t' % s, 'cc', self.fa, self.fs, 10, ACCENT)
            self.cache[s] = np.asarray(img).copy()
        return self.cache[s]


def background(view, label, readout):
    img = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(img)
    fl = font('semibold', 42)
    d.text((LEFT, 92), label, font=fl, fill=TEXT, anchor='ls')
    assert LEFT + fl.getlength(label) + 40 < readout.x0, 'label runs into the time readout'
    d.text((LEFT, 132), SUBTITLE[view], font=font('regular', 24), fill=MUTED, anchor='ls')
    x0, y0, w, h = picture_box(view)
    d.rectangle((x0 - 1, y0 - 1, x0 + w, y0 + h), outline=LINE, width=1)
    # colour bar: 768 px, each of the 256 colours on 3 px, logarithmic from 0.008 to 5
    bx, bw, by0, by1 = LEFT, 768, 980, 996
    for k in range(bw):
        d.line((bx + k, by0, bx + k, by1 - 1), fill=tuple(int(v) for v in LUT8[min(255, (k * 256) // bw)]))
    lo, hi = math.log10(.008), math.log10(5)
    fs = font('regular', 20)
    for v, txt in ((.008, '0.008'), (.1, '0.1'), (1, '1'), (5, '5')):
        x = bx + (math.log10(v) - lo) / (hi - lo) * bw
        xi = min(max(int(round(x)), bx), bx + bw - 1)
        d.line((xi, by1, xi, by1 + 6), fill=MUTED, width=1)
        anchor = 'ls' if v == .008 else ('rs' if v == 5 else 'ms')
        d.text((bx if v == .008 else (bx + bw if v == 5 else x), 1026), txt, font=fs, fill=MUTED, anchor=anchor)
    # unit, right of the bar: Σ / (ρ_{c,0} R)
    fu, fsub = font('regular', 24), font('regular', 16)
    x = draw_sub(d, bx + bw + 24, by1, '\u03a3 / (\u03c1', 'c,0', fu, fsub, 5, TEXT)
    d.text((x + 1, by1), ' R)', font=fu, fill=TEXT, anchor='ls')
    d.text((RIGHT, 1026), 'Cloud Studio', font=font('regular', 20), fill=MUTED, anchor='rs')
    return np.asarray(img).copy()


# ------------------------------------------------------------------ timing
def schedule(times):
    """Frame list [(state, weight of the next state, time)] and the film frame of each saved state."""
    t0 = times[0]
    pos = [int(round((t - t0) * FRAMES_PER_TCC)) for t in times]
    assert all(b > a for a, b in zip(pos[:-1], pos[1:])), 'two saved states fall on one film frame'
    out = [(0, 0.0, times[0])] * HOLD_START
    for i in range(len(times) - 1):
        span = pos[i + 1] - pos[i]
        for k in range(span):
            w = k / span
            out.append((i, w, times[i] + w * (times[i + 1] - times[i])))
    out += [(len(times) - 1, 0.0, times[-1])] * (1 + HOLD_END)
    return out, [HOLD_START + p for p in pos]


# ------------------------------------------------------------------ ffmpeg
def encode_cmd(dest, crf):
    return ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H), '-r', str(FPS),
            '-i', 'pipe:0', '-an', '-vf', 'scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv420p,'
            'setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709:range=tv',
            '-c:v', 'libx264', '-preset', 'medium', '-crf', str(crf), '-profile:v', 'high', '-g', str(FPS), '-threads', '4',
            '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv', '-movflags', '+faststart', str(dest)]


def ffprobe(p):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_frames', '-show_entries',
                        'stream=codec_name,profile,pix_fmt,width,height,r_frame_rate,avg_frame_rate,nb_frames,nb_read_frames,'
                        'color_space,color_transfer,color_primaries,color_range:format=duration,size,nb_streams',
                        '-of', 'json', str(p)], capture_output=True, text=True, check=True)
    j = json.loads(r.stdout); s = j['streams'][0]
    return dict(codec=s['codec_name'], profile=s.get('profile'), pix_fmt=s['pix_fmt'], width=s['width'], height=s['height'],
                r_frame_rate=s['r_frame_rate'], avg_frame_rate=s['avg_frame_rate'], frames=int(s['nb_read_frames']),
                frames_in_header=int(s['nb_frames']) if s.get('nb_frames') else None, color_space=s.get('color_space'),
                color_transfer=s.get('color_transfer'), color_primaries=s.get('color_primaries'), color_range=s.get('color_range'),
                streams=int(j['format']['nb_streams']), duration=float(j['format']['duration']), bytes=int(j['format']['size']))


def full_decode(p):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-v', 'error', '-xerror', '-i', str(p), '-map', '0:v:0', '-f', 'null', '-'],
                       capture_output=True, text=True)
    return dict(returncode=r.returncode, errors=r.stderr.strip()[:2000], ok=r.returncode == 0 and not r.stderr.strip())


def decode_frames(p, indices):
    """Decode the given frame numbers (sorted, distinct) as RGB arrays (BT.709, limited range, as tagged)."""
    idx = sorted(set(int(i) for i in indices))
    sel = '+'.join('eq(n\\,%d)' % i for i in idx)
    r = subprocess.run(['ffmpeg', '-hide_banner', '-v', 'error', '-i', str(p), '-vf',
                        'select=%s,scale=in_color_matrix=bt709:in_range=tv:flags=accurate_rnd+full_chroma_int,format=rgb24' % sel,
                        '-fps_mode', 'passthrough', '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1'], capture_output=True, check=True)
    arr = np.frombuffer(r.stdout, dtype=np.uint8)
    assert arr.size == len(idx) * H * W * 3, ('decoded size', arr.size, len(idx))
    return dict(zip(idx, arr.reshape(len(idx), H, W, 3)))


# ------------------------------------------------------------------ the renderer
def _as_rows(rows, view):
    rows = np.asarray(rows)
    assert rows.dtype == np.uint8 and rows.ndim == 4 and rows.shape[1:] == ROW_SHAPE[view], (view, rows.dtype, rows.shape)
    return rows


def render_films(edge_rows, face_rows, times, label, out_dir, *, upscale='auto', crf=18, tmp_dir=None, verify=True, check_state=50,
                 reference_rows=None, log=None):
    log = log or (lambda *x: print(time.strftime('%H:%M:%S'), 'film_style', *x, flush=True))
    rows = dict(edge=_as_rows(edge_rows, 'edge'), face=_as_rows(face_rows, 'face'))
    times = [float(t) for t in times]
    n = len(times)
    assert rows['edge'].shape[0] == n and rows['face'].shape[0] == n, ('states', rows['edge'].shape[0], rows['face'].shape[0], n)
    assert n >= 2 and all(np.isfinite(times)) and all(b > a for a, b in zip(times[:-1], times[1:])), 'times must increase'
    assert isinstance(label, str) and label.strip() == label and label and not DASH.search(label), ('label', label)
    if upscale == 'auto':
        upscale = 'nearest' if blocky(rows['edge']) and blocky(rows['face']) else 'lanczos'
    assert upscale in ('lanczos', 'nearest'), upscale
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tmp_dir) if tmp_dir else out_dir; tmp_dir.mkdir(parents=True, exist_ok=True)
    sched, state_frames = schedule(times)
    ks = min(check_state, n - 1)
    longest = max(('%.2f' % t for t in times), key=len)
    result = dict(renderer=RENDERER,
                  style=dict(width=W, height=H, codec='h264 High', pix_fmt='yuv420p', colour='bt709 limited range', fps=FPS,
                             frames_per_tcc=FRAMES_PER_TCC, hold_start_frames=HOLD_START, hold_end_frames=HOLD_END, picture_scale=SCALE,
                             upscale=upscale, crf_start=crf, font='Segoe UI (Semibold label, Regular otherwise)',
                             text=dict(label=label, subtitle_edge=SUBTITLE['edge'], subtitle_face=SUBTITLE['face'],
                                       readout='t = %.2f t with subscript cc, interpolated linearly between neighbouring states',
                                       colour_bar_ticks=['0.008', '0.1', '1', '5'], unit='\u03a3 / (\u03c1 with subscript c,0, then R)',
                                       corner='Cloud Studio'),
                             colours=dict(background='#0b1017', text='#ecf1f5', grey='#9baab9', readout='#e5ba83', frame_line='#26323f')),
                  states=n, t_first=times[0], t_last=times[-1], frames=len(sched), state_frames=state_frames)
    for view in ('edge', 'face'):
        s0 = time.perf_counter()
        x0, y0, w, h = picture_box(view)
        big = np.stack([scale_picture(r, view, upscale) for r in rows[view]])
        ro = Readout(longest)
        bg = background(view, label, ro)
        dest = out_dir / ('film-%s.mp4' % view)
        tmp = tmp_dir / ('.film-%s.%d.mp4' % (view, os.getpid()))
        c = crf
        while True:
            p = subprocess.Popen(encode_cmd(tmp, c), stdin=subprocess.PIPE)
            expected = {}
            try:
                fr = bg.copy()
                pair, fa, fb = None, None, None
                for f_no, (i, wgt, t) in enumerate(sched):
                    if wgt == 0:
                        pic = big[i]
                    else:
                        if pair != i:
                            pair, fa, fb = i, big[i].astype(np.float32), big[i + 1].astype(np.float32)
                        pic = np.minimum(fa * (1 - wgt) + fb * wgt + .5, 255).astype(np.uint8)
                    fr[y0:y0 + h, x0:x0 + w] = pic                      # the picture (cross faded) first,
                    fr[ro.y0:ro.y1, ro.x0:ro.x1] = ro.patch('%.2f' % t)  # then the time readout; the other text is on the background
                    if f_no == state_frames[ks]: expected['state'] = fr.copy()
                    p.stdin.write(memoryview(fr))
                p.stdin.close()
                assert p.wait() == 0, 'ffmpeg failed'
            finally:
                if p.poll() is None: p.kill()
            size = os.path.getsize(tmp)
            if size <= MAX_BYTES or c >= 30: break
            log(view, 'film is %d bytes at crf %d, trying crf %d' % (size, c, c + 2)); c += 2
        assert size <= MAX_BYTES, ('film too large', size)
        info = dict(frames=len(sched), crf=c, upscale=upscale, seconds_to_make=None)
        if verify:
            pr = ffprobe(tmp)
            ok = (pr['codec'] == 'h264' and pr['profile'] == 'High' and pr['pix_fmt'] == 'yuv420p' and (pr['width'], pr['height']) == (W, H)
                  and pr['r_frame_rate'] == '%d/1' % FPS and pr['avg_frame_rate'] == '%d/1' % FPS and pr['frames'] == len(sched)
                  and pr['color_space'] == 'bt709' and pr['color_primaries'] == 'bt709' and pr['color_transfer'] == 'bt709'
                  and pr['color_range'] == 'tv' and pr['streams'] == 1)
            assert ok, ('ffprobe', pr)
            dec = full_decode(tmp)
            assert dec['ok'], ('decode', dec)
            ref = (reference_rows or {}).get(view)
            ref_big = scale_picture(np.asarray(ref)[ks], view, upscale) if ref is not None else big[ks]
            got = decode_frames(tmp, [state_frames[ks]])[state_frames[ks]].astype(np.int16)
            pic = got[y0:y0 + h, x0:x0 + w]
            dpic = np.abs(pic - ref_big.astype(np.int16)); dall = np.abs(got - expected['state'].astype(np.int16))
            info.update(ffprobe=pr, full_decode=dec,
                        state_check=dict(state=ks, t_tcc=times[ks], film_frame=state_frames[ks],
                                         reference='sprite row %d scaled %d times (%s)' % (ks, SCALE, upscale),
                                         input_picture_equals_reference=bool(np.array_equal(big[ks], ref_big)),
                                         picture_mean_abs_diff=float(dpic.mean()), picture_max_abs_diff=int(dpic.max()),
                                         picture_pixels_off_by_more_than_8=int((dpic.max(axis=-1) > 8).sum()),
                                         whole_frame_mean_abs_diff=float(dall.mean()), whole_frame_max_abs_diff=int(dall.max())))
            assert info['state_check']['picture_mean_abs_diff'] < 3, info['state_check']
        sha = sha256_file(tmp)
        assert not_zero_filled(tmp), 'zero filled film ' + str(tmp)
        if tmp.parent.resolve() == dest.parent.resolve():
            os.replace(tmp, dest)
        else:
            try:
                os.replace(tmp, dest)
            except OSError:
                shutil.copyfile(tmp, dest); os.remove(tmp)
        assert sha256_file(dest) == sha and not_zero_filled(dest), 'film changed while it was moved: ' + str(dest)
        info.update(bytes=os.path.getsize(dest), sha256=sha, seconds_to_make=round(time.perf_counter() - s0, 1))
        result[view] = info
        log(view, '%d frames, %.2f MB, crf %d, %s, %.0f s' % (info['frames'], info['bytes'] / 1e6, c, upscale, info['seconds_to_make'])
            + ('' if not verify else ', state %d picture mean |diff| %.3f' % (ks, info['state_check']['picture_mean_abs_diff'])))
        del big
    return result


# ------------------------------------------------------------------ cache adapters and the command line
def load_frames(spec):
    """<kind>:<path> -> (edge_rows, face_rows, times, source description)."""
    kind, _, path = spec.partition(':')
    path = Path(path)
    if kind == 'grid':
        z = np.load(path)
        ce, cf, times = z['col_edge'], z['col_face'], [float(t) for t in z['times']]
        edge = np.stack([color(to_sprite(c.astype(np.float64))) for c in ce]); face = np.stack([color(to_sprite(c.astype(np.float64))) for c in cf])
        src = dict(kind='grid', made_by='stage_grid.py', path=win_path(path), sha256=sha256_file(path), native_cells=int(ce.shape[1]),
                   rows='colour mapped here from the float32 column density maps, same table and row geometry as stage_grid.py')
    elif kind == 'other':
        z = np.load(path)
        edge, face, times = np.asarray(z['rgb_e']), np.asarray(z['rgb_f']), [float(t) for t in z['t_tcc']]
        src = dict(kind='other', made_by='stage_run2.py', path=win_path(path), sha256=sha256_file(path), rows='sprite rows stored in the cache')
    elif kind == 'sprites':
        e = np.asarray(Image.open(path / 'edge.png').convert('RGB')); f = np.asarray(Image.open(path / 'face.png').convert('RGB'))
        times = [float(t) for t in json.loads((path / 'entry.json').read_text(encoding='utf-8'))['times']]
        edge, face = e.reshape(-1, 128, 256, 3), f.reshape(-1, 128, 128, 3)
        src = dict(kind='sprites', path=win_path(path), sha256=dict(edge=sha256_file(path / 'edge.png'), face=sha256_file(path / 'face.png')),
                   rows='edge.png and face.png of the run folder')
    else:
        raise SystemExit('--frames-from must be grid:<npz>, other:<npz> or sprites:<run folder>')
    return np.ascontiguousarray(edge, dtype=np.uint8), np.ascontiguousarray(face, dtype=np.uint8), times, src


def write_json_checked(dest, obj, tmp_dir):
    data = json.dumps(obj, indent=1, ensure_ascii=False).encode('utf-8')
    tmp = Path(tmp_dir) / ('.%s.%d.tmp' % (Path(dest).name, os.getpid()))
    with open(tmp, 'wb') as fh:
        fh.write(data); fh.flush(); os.fsync(fh.fileno())
    try:
        os.replace(tmp, dest)
    except OSError:
        shutil.copyfile(tmp, dest); os.remove(tmp)
    back = Path(dest).read_bytes()
    assert back == data and not_zero_filled(dest) and json.loads(back.decode('utf-8')) == obj, 'report did not read back: ' + str(dest)


def redraw(rid, frames_from, label, out, tmp=None, crf=18, upscale='auto', report=True, log=None):
    """Render the two films of one run into its folder and record them in its stage_report.json (command line and batch use)."""
    out = Path(out); tmp = Path(tmp) if tmp else out
    edge, face, times, src = load_frames(frames_from)
    entry_p = out / 'entry.json'
    if entry_p.exists():
        entry = json.loads(entry_p.read_text(encoding='utf-8'))
        assert entry.get('id', rid) == rid, ('id', entry.get('id'), rid)
        assert entry['label'] == label, ('label differs from entry.json', entry['label'], label)
        assert [float(t) for t in entry['times']] == times, 'source times differ from entry.json times'
        src['times_equal_entry_json'] = True
    refs = None
    if (out / 'edge.png').exists() and (out / 'face.png').exists():
        se = np.asarray(Image.open(out / 'edge.png').convert('RGB')).reshape(-1, 128, 256, 3)
        sf = np.asarray(Image.open(out / 'face.png').convert('RGB')).reshape(-1, 128, 128, 3)
        assert se.shape[0] == len(times) and sf.shape[0] == len(times), 'sprite rows do not match the number of states'
        refs = dict(edge=se, face=sf)
        cmp_ = {}
        for v, a_, b_ in (('edge', edge, se), ('face', face, sf)):
            d = np.abs(a_.astype(np.int16) - b_.astype(np.int16))
            px = d.max(axis=-1) > 0
            cmp_[v] = dict(pixels_differing=int(px.sum()), of_pixels=int(px.size), states_with_differences=int(px.any(axis=(1, 2)).sum()),
                           max_abs_diff=int(d.max()))
        src['rows_vs_sprite_rows'] = cmp_
        assert all(c['max_abs_diff'] <= 16 and c['pixels_differing'] <= 1000 for c in cmp_.values()), ('source rows differ from the sprite rows', cmp_)
    films = render_films(edge, face, times, label, out, upscale=upscale, crf=crf, tmp_dir=tmp, reference_rows=refs, log=log)
    films['source'] = src
    films['label'] = label
    films['made'] = time.strftime('%Y-%m-%d %H:%M:%S')
    rp = out / 'stage_report.json'
    if report and rp.exists():
        old = json.loads(rp.read_text(encoding='utf-8'))
        prev = [k for k in ('film',) if k in old] + (['checks.films'] if isinstance(old.get('checks'), dict) and 'films' in old['checks'] else [])
        films['replaces'] = ('the films were redrawn in the one film style; the frame counts and settings under '
                             + ' and '.join('"%s"' % k for k in prev) + ' belong to the earlier films') if prev else 'first record of the films'
        new = dict(old); new['films'] = films
        write_json_checked(rp, new, tmp)
        back = json.loads(rp.read_text(encoding='utf-8'))
        assert {k: v for k, v in back.items() if k != 'films'} == {k: v for k, v in old.items() if k != 'films'}, 'report changed outside "films"'
    return films


def main(argv=None):
    ap = argparse.ArgumentParser(description='Render film-edge.mp4 and film-face.mp4 of one run in the Cloud Studio film style.')
    ap.add_argument('--id', required=True)
    ap.add_argument('--frames-from', required=True, help='grid:<stage_grid cache .npz>, other:<stage_run2 cache .npz> or sprites:<run folder>')
    ap.add_argument('--label', required=True)
    ap.add_argument('--out', required=True, help='run folder that receives the films')
    ap.add_argument('--tmp', default='', help='folder for the films while they are written (default: --out)')
    ap.add_argument('--crf', type=int, default=18)
    ap.add_argument('--upscale', default='auto', choices=['auto', 'lanczos', 'nearest'])
    ap.add_argument('--no-report', action='store_true', help='do not add the "films" section to stage_report.json')
    a = ap.parse_args(argv)
    films = redraw(a.id, a.frames_from, a.label, a.out, tmp=a.tmp or None, crf=a.crf, upscale=a.upscale, report=not a.no_report)
    print(json.dumps({v: {k: films[v][k] for k in ('frames', 'bytes', 'crf', 'upscale', 'sha256')} for v in ('edge', 'face')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
