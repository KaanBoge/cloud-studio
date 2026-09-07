"""Native-output 3D isosurface comparison with strict metadata/time checks.

Plan: {"panels":[{"diagnostics":"schema2.json","center_code":[0,0,0]}, ...]}.
Centers are explicit code-coordinate inputs, recorded in the output provenance.
Only uniform 3D native grids are supported. No random face thinning, no guessed
chi/Mach/time, no late-frame substitution, and no claim that an empty surface
proves mixing (it may also reflect material leaving the domain).
"""
import argparse
import json
import math
from pathlib import Path
import numpy as np
from run_params import parse_file


def select_panels(plan,time,tolerance):
    chosen=[]
    for entry in plan['panels']:
        d=json.loads(Path(entry['diagnostics']).read_text())
        if d.get('schema_version')!=2 or not d.get('comparison_group'):
            raise ValueError('Schema-2 diagnostics and a reviewed comparison group are required')
        p=parse_file(d['parameters']['source'])
        if not p or p['parameter_sha256']!=d['parameters']['parameter_sha256']:
            raise ValueError('Parameter file changed after diagnostics; recompute')
        rows=d['series']
        times=np.array([r['t_over_tcc'] for r in rows])
        if not len(times) or not np.all(np.isfinite(times)) or np.any(np.diff(times)<=0):
            raise ValueError('Invalid native time series')
        row=rows[int(np.argmin(abs(times-time)))]
        if abs(row['t_over_tcc']-time)>tolerance:
            raise ValueError(f"{d['kind']}: no measured snapshot at requested common time")
        if not row['grid']['uniform']:
            raise ValueError('Adaptive-grid isosurface sampling needs a separately validated reader')
        center=np.asarray(entry['center_code'],float)
        if center.shape!=(3,) or not np.all(np.isfinite(center)):
            raise ValueError('Explicit three-dimensional center is required')
        chosen.append({'kind':d['kind'],'parameters':p,'row':row,'center_code':center.tolist(),
                       'group':d['comparison_group']})
    if not chosen: raise ValueError('No panels')
    if len({p['group'] for p in chosen})!=1:
        raise ValueError('Mixed comparison groups')
    if len({tuple(p['row']['grid']['finest_equivalent_dimensions']) for p in chosen})!=1:
        raise ValueError('Different measured resolutions')
    codes=sorted({p['kind'] for p in chosen});chis=sorted({p['parameters']['chi'] for p in chosen})
    pairs={(p['kind'],p['parameters']['chi']) for p in chosen}
    if len(chosen)!=len(pairs) or len(pairs)!=len(codes)*len(chis):
        raise ValueError('Missing/duplicate code-overdensity comparison panel')
    return chosen,codes,chis


def native_density(panel):
    kind=panel['kind']; row=panel['row'];path=row['snapshot'];p=panel['parameters']
    if kind=='ramses':
        from ramses_native import read_output
        meta,c=read_output(path);xyz=c[:,:3];widths=np.repeat(c[:,3,None],3,axis=1)
        rho=c[:,4];time=meta['time']
    else:
        import yt
        yt.set_log_level(40);ds=yt.load(path);ad=ds.all_data()
        xyz=np.stack([ad['index',a].to_value('code_length') for a in 'xyz'],axis=1)
        widths=np.stack([ad['index','d'+a].to_value('code_length') for a in 'xyz'],axis=1)
        rho=ad['gas','density'].to_value('code_density');time=float(ds.current_time.to_value('code_time'))
    if not math.isclose(time,row['time_code'],rel_tol=1e-10,abs_tol=1e-12):
        raise ValueError('Native snapshot time changed or is inconsistent')
    if kind=='apk': xyz=xyz[:,[1,0,2]];widths=widths[:,[1,0,2]]
    center=np.array(panel['center_code'])
    if kind=='apk':center=center[[1,0,2]]
    xyz=(xyz-center)/p['r_cloud'];widths=widths/p['r_cloud']
    if not np.allclose(widths,widths[0],rtol=1e-6):raise ValueError('Not a uniform grid')
    lo=xyz.min(axis=0);spacing=widths[0]
    dims=np.array(row['grid']['finest_equivalent_dimensions'])
    if len(rho)!=int(np.prod(dims)):raise ValueError('Cell count mismatch')
    idx=np.rint((xyz-lo)/spacing).astype(int)
    flat=np.ravel_multi_index(idx.T,dims)
    if len(np.unique(flat))!=len(rho):raise ValueError('Duplicate or missing native grid locations')
    if not np.allclose(lo-spacing/2,[-3,-5,-5]) or not np.allclose(xyz.max(axis=0)+spacing/2,[17,5,5]):
        raise ValueError('Domain/center does not match the comparison window')
    field=np.empty(tuple(dims));field.ravel()[flat]=rho/(p['chi']*p['rho_wind'])
    if not np.all(np.isfinite(field)):raise ValueError('Non-finite native density')
    return field,lo,spacing


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--plan',required=True);ap.add_argument('--out',required=True)
    ap.add_argument('--time',type=float,required=True);ap.add_argument('--tolerance',type=float,default=1e-5)
    a=ap.parse_args();out=Path(a.out);report=Path(str(out)+'.json')
    if out.exists() or report.exists():raise FileExistsError('Choose a fresh output path')
    if not math.isfinite(a.time) or a.time<0 or not math.isfinite(a.tolerance) or a.tolerance<0:
        raise ValueError('Invalid time/tolerance')
    chosen,codes,chis=select_panels(json.loads(Path(a.plan).read_text()),a.time,a.tolerance)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    from skimage.measure import marching_cubes
    fig=plt.figure(figsize=(5*len(codes),4*len(chis)),dpi=140)
    for panel in chosen:
        r=chis.index(panel['parameters']['chi']);c=codes.index(panel['kind'])
        ax=fig.add_subplot(len(chis),len(codes),r*len(codes)+c+1,projection='3d')
        field,lo,spacing=native_density(panel)
        for level,color,alpha in ((.15,'#0072B2',.22),(.6,'#D55E00',.9)):
            if field.min()<level<field.max():
                vertices,faces,_,_=marching_cubes(field,level=level,spacing=spacing)
                ax.add_collection3d(Poly3DCollection((vertices+lo)[faces],facecolors=color,edgecolors='none',alpha=alpha))
        ax.set(xlim=(-3,17),ylim=(-5,5),zlim=(-5,5),xlabel='x / R',ylabel='y / R',zlabel='z / R')
        ax.set_box_aspect((2,1,1));ax.view_init(17,-66)
        ax.set_xticks([0,8,16]);ax.set_yticks([-4,0,4]);ax.set_zticks([-4,0,4])
        ax.set_title(f"{panel['kind']}, chi={panel['parameters']['chi']:g}\nt = {panel['row']['t_over_tcc']:.6g} t_cc",fontsize=10)
    dims=chosen[0]['row']['grid']['finest_equivalent_dimensions']
    fig.suptitle(f"{chosen[0]['group']}\n{' x '.join(map(str,dims))}; rho/rho_cloud,0 = 0.15 (blue), 0.6 (orange)",fontsize=11)
    fig.tight_layout(rect=(0,0,1,.94));fig.savefig(out)
    report.write_text(json.dumps({'panels':chosen,'requested_time':a.time,'tolerance':a.tolerance,
                                 'note':'An empty isosurface alone is not proof of mixing or of material remaining in the box.'},indent=2))


if __name__=='__main__': main()
