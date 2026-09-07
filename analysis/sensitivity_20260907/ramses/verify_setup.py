"""Canonical native-IC cross-check and real invalid-mode negative control."""
import json
from pathlib import Path
import subprocess
import numpy as np
from run_ramses import ROOT, read_output, raw, parameters, input_for, save

def main():
    control=ROOT/'smokes/L3_chi100_sharp13'
    params=parameters(control/'run.nml');new=raw(control/'output_00001',params)
    meta,old=read_output('/home/kaan/ic_audit_20260907/ramses_rect_tests/chi100/output_00001')
    old=old[np.lexsort((old[:,2],old[:,1],old[:,0]))]
    compared=dict(coordinates=np.array_equal(old[:,:3],new['xyz']),density=np.array_equal(old[:,4],new['rho']),
        velocity=np.array_equal(old[:,5:8],new['vel']),tracer=np.array_equal(old[:,9],new['tracer_concentration']))
    pressure=float(np.max(abs(old[:,8]-new['pressure'])))
    print(json.dumps(dict(exact=compared,pressure=pressure,max_abs={key:float(np.max(abs(a-b))) for key,a,b in (
        ('xyz',old[:,:3],new['xyz']),('rho',old[:,4],new['rho']),('vel',old[:,5:8],new['vel']),
        ('tracer',old[:,9],new['tracer_concentration']))})),flush=True)
    # Different native builds/MPI layouts need not be bitwise identical. This
    # extra cross-build check permits roundoff; the actual within-binary pairs
    # are separately required to match initial density/tracer/grid exactly.
    relative_density=float(np.max(abs(old[:,4]-new['rho'])/old[:,4]))
    tracer_error=float(np.max(abs(old[:,9]-new['tracer_concentration'])))
    if not compared['coordinates'] or not compared['velocity'] or relative_density>1e-13 or tracer_error>1e-13 or pressure>1e-13:
        raise ValueError('Corrected IC differs beyond roundoff from audited native control')
    negative=ROOT/'invalid_mode';negative.mkdir(exist_ok=False)
    (negative/'run.nml').write_text(input_for(3,0,True).replace('velocity_ic = 0','velocity_ic = 2'))
    with (negative/'run.log').open('x') as log:
        result=subprocess.run(['mpirun','--bind-to','core','-np','8',str(ROOT/'ramses_pair3d'),'run.nml'],
            cwd=negative,stdout=log,stderr=subprocess.STDOUT,timeout=60)
    text=(negative/'run.log').read_text()
    if 'velocity_ic must be 0 or 1' not in text or list(negative.glob('output_*/hydro_*.out*')):
        raise ValueError('Native invalid mode was not rejected before hydro output')
    report=dict(status='passed',canonical_ic_bitwise_comparison=compared,pressure_max_difference=pressure,
                density_max_relative_difference=relative_density,tracer_max_difference=tracer_error,
                canonical_cross_build_tolerance=1e-13,within_new_pair_requires_exact_density_tracer=True,
                native_invalid_mode_rejected=True,invalid_mode_returncode=result.returncode,
                negative_control_directory=str(negative))
    save(ROOT/'setup_validation.json',report);print(json.dumps(report),flush=True)

if __name__=='__main__':main()
