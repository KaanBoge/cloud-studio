"""Verify physical metadata in figure inputs, independently of their group label.

A group name is not a certificate of matching boundary conditions or tracer
definitions. These checks catch measurable mismatches but do not certify those
remaining solver-level requirements.
"""
import math
import re
from pathlib import Path
from run_params import parse_file

KIND_ALIASES = {'athpp':'athena', 'athw':'athena', 'apk':'apk', 'enzo':'enzo',
                'flash':'flash', 'flashx':'flash', 'ramses':'ramses'}


def verified_parameters(diagnostic):
    old = diagnostic['parameters']
    current = parse_file(old['source'])
    if not current or current['parameter_sha256'] != old['parameter_sha256']:
        raise ValueError('Parameter file changed or is unreadable; recompute diagnostics')
    if current.get('kind') != KIND_ALIASES.get(diagnostic['kind']):
        raise ValueError('Code label does not match parameter-file format')
    raw=Path(old['source']).read_text()
    clean='\n'.join(re.split(r'#|!|//',line,maxsplit=1)[0] for line in raw.splitlines())
    # The current figure pipeline is certified only for the nonradiative,
    # fixed-frame audit. A cooling block, even one accidentally disabled,
    # must not sneak into that group. Tracking needs lab-frame metadata first.
    if re.search(r'<cooling>',clean,re.I):
        raise ValueError('Cooling configuration requires separate reviewed diagnostics')
    if re.search(r'\bgalilean_(?:tracking|shift)\s*=\s*(true|1)\b',clean,re.I):
        raise ValueError('Frame-tracking configuration requires lab-frame-aware diagnostics')
    # Re-reading the file prevents a correct hash from hiding edited metadata
    # in an intermediate JSON file. Missing values must not compare as equal.
    for key in ('chi','r_cloud','rho_wind','p_wind','v_wind','t_cc','mach','gamma','rv_scale'):
        a,b = current.get(key),old.get(key)
        if a is None or b is None or not math.isfinite(a) or not math.isfinite(b) or a <= 0:
            raise ValueError(f'Missing/non-positive physical parameter: {key}')
        if not math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-14):
            raise ValueError(f'Diagnostic parameter differs from native input: {key}')
    for row in diagnostic['series']:
        a,b = row['time_code']/current['t_cc'],row['t_over_tcc']
        if not math.isfinite(a) or not math.isfinite(b) or not math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-12):
            raise ValueError('Stored normalized time is inconsistent with the native time and t_cc')
    return current


def require_common_physics(runs):
    if not runs:
        raise ValueError('No diagnostic runs')
    params = [verified_parameters(d) for d in runs]
    # R and ambient dimensional units may differ (FLASH R=.1, Athena++ R=1).
    # chi intentionally varies across columns. Compare dimensionless physics.
    for key in ('mach','gamma','rv_scale'):
        ref=params[0][key]
        if any(not math.isclose(p[key],ref,rel_tol=1e-6,abs_tol=1e-12) for p in params[1:]):
            raise ValueError(f'Mixed physical {key} despite a shared comparison-group name')
    for d in runs:
        grid=d.get('initial_grid',{})
        dims=grid.get('finest_equivalent_dimensions')
        if not dims or len(dims)!=3 or any(not isinstance(n,int) or n<=0 for n in dims):
            raise ValueError('Invalid measured 3D resolution')
        widths=grid.get('domain_width_over_R')
        # Pre-followup APK metadata was in native axis order; admit that known
        # legacy layout here, not an arbitrary permutation for other solvers.
        allowed=([20,10,10],[10,20,10]) if d['kind']=='apk' else ([20,10,10],)
        if not widths or not any(len(widths)==3 and all(math.isclose(a,b,rel_tol=1e-6) for a,b in zip(widths,w)) for w in allowed):
            raise ValueError('Domain dimensions differ from the reviewed 20R x 10R x 10R box')
    return params
