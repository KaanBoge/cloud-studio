import h5py
from pathlib import Path
for code, ext, name in [('athenapp','athdf','athpp'),('athenapk','phdf','apk')]:
    root=Path('/home/kaan/codes')/code/'runs/RESTART_sharp13_20260907_L3_chi100'
    p=sorted(root.glob('*.'+ext))[0]
    print(name,p)
    with h5py.File(p) as f:
        print('root attrs',dict(f.attrs))
        def show(k,v):
            if isinstance(v,h5py.Dataset):
                print(k,v.shape,v.dtype)
                if v.size<20:print(v[...])
            elif k=='Info':print('Info',dict(v.attrs))
        f.visititems(show)
