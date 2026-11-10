"""Create separate 60 fps blended display previews; source movies are immutable.

Only the new derivatives are encoded. Native fields and accepted reductions are
never read. CUDA's video encoder is used one job at a time, at below-normal
process priority. Every output is checked for frame rate, extent and duration.
"""
from pathlib import Path
import json,struct,sys,subprocess,time,os,hashlib
ROOT=Path(__file__).resolve().parents[1];os.chdir(ROOT)
sys.path.insert(0,'D:/CloudStudio-tools')
import imageio_ffmpeg
FF=imageio_ffmpeg.get_ffmpeg_exe()
def boxes(b,start=0,end=None):
    end=len(b) if end is None else end;p=start
    while p+8<=end:
        n,t=struct.unpack_from('>I4s',b,p);h=8
        if n==1:n=struct.unpack_from('>Q',b,p+8)[0];h=16
        if n==0:n=end-p
        if n<h or p+n>end:raise ValueError('Invalid MP4 box')
        yield t,p+h,p+n;p+=n
def probe(p):
    moov=None
    with p.open('rb') as f:
        while h:=f.read(8):
            n,t=struct.unpack('>I4s',h);head=8
            if n==1:n=struct.unpack('>Q',f.read(8))[0];head=16
            if n<head:raise ValueError('Invalid MP4')
            if t==b'moov':moov=f.read(n-head);break
            f.seek(n-head,1)
    if moov is None:raise ValueError('No movie metadata')
    for t,a,z in boxes(moov):
        if t!=b'trak':continue
        found={}
        def walk(start,end):
            for k,i,j in boxes(moov,start,end):
                if k in (b'mdia',b'minf',b'stbl'):walk(i,j)
                else:found[k]=(i,j)
        walk(a,z)
        if b'hdlr' not in found or moov[found[b'hdlr'][0]+8:found[b'hdlr'][0]+12]!=b'vide':continue
        a,z=found[b'tkhd'];width,height=struct.unpack_from('>II',moov,z-8)
        a,z=found[b'mdhd'];off=a+(20 if moov[a] else 12);scale=struct.unpack_from('>I',moov,off)[0]
        a,z=found[b'stts'];count=struct.unpack_from('>I',moov,a+4)[0]
        entries=[struct.unpack_from('>II',moov,a+8+i*8) for i in range(count)]
        return dict(width=width//65536,height=height//65536,duration=sum(n*d for n,d in entries)/scale,frames=sum(n for n,d in entries),fps=sorted({round(scale/d,6) for n,d in entries if d}))
    raise ValueError('No video track')

def main():
    out=ROOT/'assets/smooth60';out.mkdir(exist_ok=True)
    receipt=ROOT/'analysis/smooth60_receipt.json'
    completed=json.loads(receipt.read_text())['files'] if receipt.exists() else {}
    recent={r['id']:r for r in json.loads((ROOT/'assets/recent/catalog.json').read_text())['runs']}
    paths=sorted((ROOT/'assets/films').glob('*.mp4'))+sorted((ROOT/'assets/movies').glob('*.mp4'))
    started=time.monotonic()
    for index,source in enumerate(paths):
        key=source.relative_to(ROOT).as_posix();name=source.parent.name+'--'+source.name;dest=out/name
        sig=hashlib.sha256(source.read_bytes()).hexdigest()
        if key in completed and completed[key]['source_sha256']==sig and dest.exists():continue
        info=probe(source);tmp=dest.with_suffix('.encoding.mp4')
        recent_film=source.parent.name=='films'
        # Recent films have exactly 11 known saved states at 2-second intervals.
        # Sample those known boundaries rather than infer extra physical states.
        vf=('fps=1/2,' if recent_film else '')+'tpad=stop_mode=clone:stop_duration=4,minterpolate=fps=60:mi_mode=blend:scd=none'
        # Override the old footer so a detached download still identifies blending.
        vf+=",drawbox=x=0:y=ih-32:w=iw:h=32:color=0x0b1017:t=fill,drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='60 fps blended preview - not additional simulation states':fontcolor=0xb9c7d6:fontsize=14:x=12:y=h-24"
        args=[FF,'-hide_banner','-loglevel','error','-nostdin','-y','-threads','1','-i',str(source),'-an','-vf',vf,'-filter_threads','1','-c:v','h264_nvenc','-preset','p4','-cq','19','-b:v','0','-pix_fmt','yuv420p','-t',str(info['duration']),'-movflags','+faststart',str(tmp)]
        result=subprocess.run(args,capture_output=True,text=True,creationflags=subprocess.BELOW_NORMAL_PRIORITY_CLASS)
        if result.returncode:raise RuntimeError(source.name+': '+result.stderr[-1200:])
        actual=probe(tmp)
        assert actual['fps']==[60.0] and actual['width']==info['width'] and actual['height']==info['height'],(source,actual)
        assert abs(actual['duration']-info['duration'])<=.05,(source,info,actual)
        os.replace(tmp,dest)
        completed[key]=dict(src=dest.relative_to(ROOT).as_posix(),source_sha256=sig,bytes=dest.stat().st_size,**actual,method='crossfade between saved images' if recent_film else 'blend between existing rendered frames',physical_interpolation=False)
        receipt.write_text(json.dumps(dict(schema='cloud-studio-60fps/1',files=completed,source_files_modified=False,audio=False),indent=2),encoding='utf-8',newline='\n')
        if index%25==0 or index==len(paths)-1:print(json.dumps(dict(done=len(completed),total=len(paths),elapsed_seconds=round(time.monotonic()-started))),flush=True)
    public={k:{f:v[f] for f in ['src','fps','duration','width','height','method']} for k,v in completed.items()}
    (ROOT/'data/smooth60.json').write_text(json.dumps(public,separators=(',',':')),encoding='utf-8',newline='\n')
    print('All 60 fps previews verified; originals preserved.',flush=True)
if __name__=='__main__':main()
