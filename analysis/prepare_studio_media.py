"""Browser-friendly media from existing derived images/video, one encoder at a time.

Legacy MP4 streams are copied losslessly with their seek index moved to the front.
Recent films are 1080p H.264, 30 fps containers holding each real saved state 2 s.
No temporal fluid interpolation and no raw simulation writes.
"""
from pathlib import Path
import sys,json,re,subprocess,struct,os,shutil
ROOT=Path(__file__).resolve().parents[1];os.chdir(ROOT)
sys.path.insert(0,'D:/CloudStudio-tools')
import imageio_ffmpeg
from PIL import Image,ImageDraw,ImageFont
FF=imageio_ffmpeg.get_ffmpeg_exe()
FONT='C:/Windows/Fonts/segoeui.ttf'
def font(n):return ImageFont.truetype(FONT,n)
def run(args):subprocess.run([FF,'-hide_banner','-loglevel','error','-nostdin','-threads','1',*args],check=True,stdout=subprocess.DEVNULL)
def atoms(p):
    out=[]
    with p.open('rb') as f:
        while f.tell()<p.stat().st_size:
            off=f.tell();h=f.read(8)
            if len(h)<8:break
            n,t=struct.unpack('>I4s',h)
            if n==1:n=struct.unpack('>Q',f.read(8))[0]
            out.append(t.decode('ascii','replace'))
            if n==0:break
            if n<8:raise ValueError('Invalid MP4 atom')
            f.seek(off+n)
    return out
catalog=json.loads((ROOT/'assets/recent/catalog.json').read_text())
films=ROOT/'assets/films';films.mkdir(exist_ok=True)
posters=ROOT/'assets/posters';posters.mkdir(exist_ok=True)
audit=[]
for r in catalog['runs']:
    for view in ('edge','face'):
        dest=films/(r['id']+'-'+view+'.mp4');poster=posters/(r['id']+'-'+view+'.jpg')
        if dest.exists() and poster.exists():
            audit.append(dict(file=str(dest.relative_to(ROOT)),states=len(r['frames']),duration_seconds=len(r['frames'])*2,width=1920,height=1080,container_fps=30,interpolated_motion=False,bytes=dest.stat().st_size))
            continue
        sprite=Image.open(ROOT/f"assets/recent/{r['id']}-{view}.png").convert('RGB')
        # One image per actual saved state. Quality increase is display resampling.
        args=[FF,'-hide_banner','-loglevel','error','-y','-threads','1','-f','rawvideo','-pix_fmt','rgb24','-s','1920x1080','-r','1/2','-i','pipe:0','-an','-vf','fps=30','-filter_threads','1','-c:v','libx264','-threads','1','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)]
        proc=subprocess.Popen(args,stdin=subprocess.PIPE)
        try:
            for i,fr in enumerate(r['frames']):
                canvas=Image.new('RGB',(1920,1080),(7,10,17));d=ImageDraw.Draw(canvas)
                d.text((74,44),'CLOUD STUDIO  /  '+r['label'],font=font(30),fill=(239,237,231))
                d.text((74,94),('EDGE-ON' if view=='edge' else 'FACE-ON')+f"    ·    t / tcc = {fr['time']:.2f}",font=font(22),fill=(177,189,207))
                frame=sprite.crop((0,i*128,sprite.width,(i+1)*128))
                size=(1536,768) if view=='edge' else (768,768)
                frame=frame.resize(size,Image.Resampling.LANCZOS);canvas.paste(frame,((1920-size[0])//2,154))
                d.text((74,981),'Total gas column density / initial cloud density × radius · log scale 0.008–5',font=font(20),fill=(175,187,202))
                d.text((74,1023),'Saved states · no interpolated fluid motion · Kaan Boge',font=font(18),fill=(139,154,174))
                for n,c in enumerate(catalog['colormap']):d.rectangle((1330+n*2,980,1331+n*2,998),fill=tuple(round(x*255) for x in c))
                d.text((1330,1006),'0.008',font=font(17),fill=(175,187,202));d.text((1825,1006),'5',font=font(17),fill=(175,187,202))
                proc.stdin.write(canvas.tobytes())
                if i==len(r['frames'])-1:
                    frame.resize((768,384) if view=='edge' else (384,384),Image.Resampling.LANCZOS).save(poster,quality=92)
            proc.stdin.close()
            if proc.wait()!=0:raise RuntimeError('Encoder failed '+str(dest))
        finally:
            if proc.stdin and not proc.stdin.closed:proc.stdin.close()
        a=atoms(dest);assert a.index('moov')<a.index('mdat')
        audit.append(dict(file=str(dest.relative_to(ROOT)),states=len(r['frames']),duration_seconds=len(r['frames'])*2,width=1920,height=1080,container_fps=30,interpolated_motion=False,bytes=dest.stat().st_size))
    print('Films ready:',r['id'],flush=True)
movies=[dict(src=str(p.relative_to(ROOT)),name=p.stem) for p in sorted((ROOT/'assets/movies').glob('*.mp4'))]
legacy=0
broken=ROOT/'assets/movies/flash3d_chi100_lref6_smooth.mp4'
if broken.stat().st_size<1000:
    retained=ROOT/'assets/movies/preserved/flash3d_chi100_lref6_smooth.mp4.invalid'
    retained.parent.mkdir(exist_ok=True)
    if not retained.exists():shutil.copy2(broken,retained)
    run(['-y','-i',str(broken.with_name('flash3d_chi100_lref6.mp4')),'-an','-vf','fps=30','-filter_threads','1','-c:v','libx264','-threads','1','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(broken)])
for m in movies:
    p=ROOT/m['src'];a=atoms(p)
    if a.index('moov')>a.index('mdat'):
        tmp=p.with_name(p.stem+'.streaming.mp4')
        run(['-y','-i',str(p),'-map','0','-c','copy','-movflags','+faststart',str(tmp)])
        b=atoms(tmp);assert b.index('moov')<b.index('mdat');os.replace(tmp,p);legacy+=1
    base=re.sub(r'_(slow|smooth)$','',m['name']);poster=posters/(base+'.jpg')
    if not poster.exists():
        run(['-y','-sseof','-0.1','-i',str(p),'-frames:v','1','-vf','scale=720:-2','-filter_threads','1','-pix_fmt','yuvj420p','-threads','1','-q:v','3',str(poster)])
        if not poster.exists():run(['-y','-i',str(p),'-frames:v','1','-vf','scale=720:-2','-filter_threads','1','-pix_fmt','yuvj420p','-threads','1','-q:v','3',str(poster)])
assert all((posters/(re.sub(r'_(slow|smooth)$','',m['name'])+'.jpg')).exists() for m in movies)
(ROOT/'analysis/media_refresh_receipt.json').write_text(json.dumps(dict(new_films=audit,legacy_films_checked=len(movies),legacy_losslessly_remuxed_this_pass=legacy,legacy_streams_preserved_except_empty_repair=True,repaired_empty_variant="flash3d_chi100_lref6_smooth.mp4: rebuilt from original, 30fps held frames; invalid 261-byte source preserved"),indent=2))
print('Media complete:',len(audit),'new films;',len(movies),'legacy files checked;',legacy,'remuxed',flush=True)
