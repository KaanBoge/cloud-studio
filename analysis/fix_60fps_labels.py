"""Replace crossfaded timestamp/footer lettering in the recent display movies.

Runs after build_60fps.py. Only derivatives change; actual saved times provide
the displayed approximate time between each pair of images.
"""
from pathlib import Path
import json, os, subprocess
from build_60fps import ROOT, FF, probe
os.chdir(ROOT)
receipt_path = Path('analysis/smooth60_receipt.json')
receipt = json.loads(receipt_path.read_text())
runs = json.loads(Path('assets/recent/catalog.json').read_text())['runs']
for run in runs:
    times = [f['time'] for f in run['frames']]
    expression = repr(times[-1])
    for i in reversed(range(len(times)-1)):
        expression = f'if(lt(t,{(i+1)*2}),{times[i]}+({times[i+1]-times[i]})*(t-{i*2})/2,{expression})'
    # drawtext expansion uses escaped colons; quote protects expression commas.
    whole = '%{eif\\:floor(' + expression + ')\\:d}'
    fraction = '%{eif\\:mod(floor((' + expression + ')*100),100)\\:d\\:2}'
    for view in ('edge', 'face'):
        record = receipt['files'][f'assets/films/{run["id"]}-{view}.mp4']
        if record.get('clean_time_labels'): continue
        dest = Path(record['src']); tmp = dest.with_suffix('.labels.mp4')
        caption = ('EDGE-ON' if view == 'edge' else 'FACE-ON') + ' - preview t/tcc ~ ' + whole + '.' + fraction
        font = "fontfile='C\\:/Windows/Fonts/segoeui.ttf'"
        vf = "drawbox=x=70:y=90:w=1350:h=42:color=0x070a11:t=fill,drawtext=" + font + ":text='" + caption + "':x=74:y=99:fontsize=22:fontcolor=0xb1bdcf"
        vf += ",drawbox=x=0:y=1018:w=1300:h=62:color=0x070a11:t=fill,drawtext=" + font + ":text='60 fps blended preview - not additional simulation states - Kaan Boge':x=74:y=1030:fontsize=18:fontcolor=0x8b9aae"
        result = subprocess.run([FF, '-v','error','-nostdin','-y','-threads','1','-i',str(dest),'-an','-vf',vf,'-filter_threads','1','-c:v','h264_nvenc','-preset','p4','-cq','19','-b:v','0','-pix_fmt','yuv420p','-movflags','+faststart',str(tmp)], capture_output=True,text=True,creationflags=subprocess.BELOW_NORMAL_PRIORITY_CLASS)
        if result.returncode: raise RuntimeError(result.stderr[-2500:])
        actual = probe(tmp)
        assert actual['fps'] == [60.0] and abs(actual['duration']-record['duration'])<.001
        os.replace(tmp,dest)
        record.update(bytes=dest.stat().st_size,clean_time_labels=True)
        receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8',newline='\n')
print('Clean approximate time labels added to all 34 recent previews.')
