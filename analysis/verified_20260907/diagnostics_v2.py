"""Native grid diagnostics with an explicit, fixed initial mass denominator.

No CLI chi/t_cc override, no overwrite, no silently skipped unreadable outputs.
Density-selected gas is not a passive-tracer measurement of cloud material.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import yt
from run_params import parse_file
from comparison_checks import KIND_ALIASES


def summarize(rho, volume, coordinate, rho_cloud_initial):
    for a in (rho,volume,coordinate):
        if not np.all(np.isfinite(a)):
            raise ValueError('Non-finite native field')
    if np.any(rho <= 0) or np.any(volume <= 0):
        raise ValueError('Non-positive density or volume')
    mass=rho*volume
    dense=rho > rho_cloud_initial/3
    dm=float(mass[dense].sum())
    return {'dense_mass':dm,'total_mass_in_box':float(mass.sum()),
            'dense_centroid_code':float(np.dot(mass[dense],coordinate[dense])/dm) if dm else None,
            'density_max':float(rho.max())}


def normalize(rows):
    rows=sorted(rows,key=lambda r:r['time_code'])
    if not rows or abs(rows[0]['t_over_tcc']) > 1e-10:
        raise ValueError('The original t=0 snapshot is required for M_dense(t)/M_dense(0)')
    m0=rows[0]['dense_mass']
    if m0 <= 0:
        raise ValueError('No dense mass resolved at t=0; this resolution cannot define the ratio')
    for i,row in enumerate(rows):
        if not all(math.isfinite(row[k]) for k in ('time_code','t_over_tcc','dense_mass')):
            raise ValueError('Non-finite diagnostic value')
        if row['dense_mass'] < 0:
            raise ValueError('Negative mass')
        if i and row['time_code'] <= rows[i-1]['time_code']:
            raise ValueError('Duplicate/non-increasing snapshot times: choose one native output per time')
        row['dense_mass_over_initial_dense_mass']=row['dense_mass']/m0
    return rows


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--params',required=True)
    p.add_argument('--kind',required=True,choices=['athpp','athw','apk','enzo','flash','flashx','ramses'])
    p.add_argument('--out',required=True)
    p.add_argument('--group',required=True,help='Explicit reviewed comparison-group ID; this is not an automatic comparability certification')
    p.add_argument('snapshots',nargs='+')
    args=p.parse_args()
    parameters=parse_file(args.params)
    if not parameters or any(parameters.get(k) is None for k in ('chi','rho_wind','t_cc')):
        raise ValueError('Missing physical parameters; refusing guessed normalization')
    if parameters.get('kind') != KIND_ALIASES[args.kind]:
        raise ValueError('Code label does not match the parameter-file format')
    print(json.dumps(parameters,indent=2,allow_nan=False))
    target=Path(args.out)
    if target.exists():
        raise FileExistsError('Choose a new output path; prior diagnostics are preserved')
    rows=[]
    grid=None
    yt.set_log_level(40)
    for fn in args.snapshots:
        if args.kind=='ramses':
            from ramses_native import read_output
            meta,c=read_output(fn)
            rho,volume,coordinate=c[:,4],c[:,3]**3,c[:,0]
            time=meta['time']
            widths=np.repeat(c[:,3,None],3,axis=1)
            spans=np.array(meta['domain_width'])
        else:
            ds=yt.load(fn)
            ad=ds.all_data()
            axis='y' if args.kind=='apk' else 'x'
            rho=ad['gas','density'].to_value('code_density')
            volume=ad['index','cell_volume'].to_value('code_length**3')
            coordinate=ad['index',axis].to_value('code_length')
            time=float(ds.current_time.to_value('code_time'))
            widths=np.stack([ad['index','d'+a].to_value('code_length') for a in 'xyz'],axis=1)
            spans=ds.domain_width.to_value('code_length')
        row=summarize(rho,volume,coordinate,parameters['chi']*parameters['rho_wind'])
        dims=np.rint(spans/widths.min(axis=0)).astype(int).tolist()
        if args.kind=='apk':
            dims=[dims[1],dims[0],dims[2]]
            spans=spans[[1,0,2]]
        current={'finest_equivalent_dimensions':dims,'leaf_cells':len(rho),
                 'uniform':bool(np.allclose(widths,widths[0],rtol=1e-6)),
                 'domain_width_over_R':(spans/parameters['r_cloud']).tolist()}
        if grid is None or time==0: grid=current
        row.update(time_code=time,
                   t_over_tcc=time/parameters['t_cc'],
                   grid=current,
                   snapshot=str(Path(fn).resolve()))
        rows.append(row)
    rows=normalize(rows)
    result={'schema_version':2,'kind':args.kind,'parameters':parameters,
            'comparison_group':args.group,'initial_grid':grid,
            'selection':'rho > rho_cloud_initial/3',
            'normalization':'M_dense(t) / M_dense(0); denominator is fixed',
            'warning':'Density-selected gas includes ambient material if it becomes dense. This is not tracer mass or a radiative cold-temperature selection.',
            'series':rows}
    with target.open('x') as f:
        json.dump(result,f,indent=2,allow_nan=False)
    print(f'Wrote {len(rows)} measured times to {target}')


if __name__=='__main__':
    main()
