"""Native MFM L3/L4 mass overlays. Requires both full pairs, preserves raw data.

No MFV failure is pooled in. Lines use actual header times. Only the reported
scalar peak separation is interpolated onto the declared common-time grid.
"""
import fcntl,json,sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0,'/home/kaan/sensitivity_20260907/gizmo/runner_mfm_l4_v1')
import mfm_l4_controls as native_l4
from smoke_gizmo import ROOT,sha,save,params
from verify_gizmo import native,sums
from run_full_l3 import check_times

def scalar_curve(rows,denominator):
    if not rows or denominator<=0:raise ValueError('Missing/invalid fixed initial denominator')
    t=np.array([r['t_over_tcc'] for r in rows],float)
    m=np.array([r['dense_mass'] for r in rows],float)/denominator
    if not np.all(np.isfinite(t)) or not np.all(np.isfinite(m)) or np.any(np.diff(t)<0):raise ValueError('Invalid time/metric series')
    if np.any((np.diff(t)==0)&(np.diff(m)!=0)):raise ValueError('Unequal diagnostics at exactly identical header time')
    if t[0]!=0 or abs(t[-1]-5)>10/(1<<29):raise ValueError('Incomplete physical interval')
    return np.interp(np.linspace(0,5,101),t,m)

def pair_metric(a,b):
    denominator=a[0]['dense_mass']
    if denominator!=b[0]['dense_mass']:raise ValueError('Within-pair initial denominators differ')
    difference=np.abs(scalar_curve(a,denominator)-scalar_curve(b,denominator))
    index=int(np.argmax(difference))
    return dict(peak_curve_difference_over_initial_mass=float(difference[index]),
        first_peak_grid_time=float(np.linspace(0,5,101)[index]),initial_dense_mass=denominator,
        final_dense_fractions=[a[-1]['dense_mass']/denominator,b[-1]['dense_mass']/denominator])

def accept_cases(batch,level):
    if level==4 and batch['status']!='complete_independent_checks':raise ValueError('L4 full pair not complete')
    cases=sorted([c for c in batch['finished'] if c['variant']=='mfm'],key=lambda c:c['mode'])
    if [c['mode'] for c in cases]!=[0,1] or any(c['status']!='complete_independent_checks' or c['level']!=level for c in cases):
        raise ValueError('Missing or uncertified native MFM pair')
    if cases[0]['physics']!=cases[1]['physics'] or cases[0]['binary_sha256']!=cases[1]['binary_sha256'] or cases[0]['input_sha256']!=cases[1]['input_sha256']:
        raise ValueError('Paired experiment settings differ')
    return cases

def resource_summary(folder):
    rows=[json.loads(x) for x in (folder/'resources.jsonl').read_text().splitlines()]
    busy=[r['busy_cpu_cores'] for r in rows if r['elapsed_seconds']>=4]
    return dict(median_busy_cpu_cores=float(np.median(busy)),samples=len(rows),resources_sha256=sha(folder/'resources.jsonl'))

def verify_case(c):
    folder=Path(c['directory']);p=c['physics'];rows=c['series'];largest=0.0
    if sha(folder/'params.txt')!=c['input_sha256'] or sha(folder/'ics.hdf5')!=c['ic_sha256']:
        raise ValueError('Native case input changed')
    if sha(ROOT/'GIZMO_mfm_pair')!=c['binary_sha256']:raise ValueError('Native binary changed')
    cadence=check_times([r['time_code'] for r in rows],p)
    expected=(8*2**c['level'])*(4*2**c['level'])**2
    for row in rows:
        path=Path(row['snapshot']);digest=sha(path)
        if digest!=row['sha256']:raise ValueError('Saved native hash differs')
        a,t=native(path,p,'mfm');measured=sums(a,p)
        if len(a['Masses'])!=expected or row['elements']!=expected or t!=row['time_code'] or t/p['t_cc']!=row['t_over_tcc']:
            raise ValueError('Actual count/time disagrees with ledger')
        for field,value in measured.items():
            error=abs(value-row[field])/max(abs(value),1e-12);largest=max(largest,error)
            if error>1e-12:raise ValueError('Direct native mass does not reproduce ledger')
        if row['dense_mass_over_initial']!=row['dense_mass']/rows[0]['dense_mass']:
            raise ValueError('Normalization is not fixed to initial mass')
        if max(row['independent_relative_errors'].values())>1e-11 or sha(path)!=digest:
            raise ValueError('Independent-reader evidence or native integrity differs')
    return dict(level=c['level'],mode=c['mode'],native_count=expected,cadence=cadence,
        wall_seconds=c['wall_seconds'],peak_child_rss_gib=c['peak_child_rss_gib'],
        direct_mass_recheck_max_relative_error=largest,
        independent_max_relative_mass_error=c['independent_max_relative_mass_error'],
        input_sha256=c['input_sha256'],ic_sha256=c['ic_sha256'],binary_sha256=c['binary_sha256'],
        initial_checks=c['initial_checks'],resources=resource_summary(folder),series=rows)

def main():
    locks=[]
    for name in ('benchmark.lock','production.lock'):
        handle=Path('/home/kaan/performance_20260907',name).open('a');fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(handle)
    native_l4.dependencies()
    dest=ROOT/'analysis_mfm_l3_l4_v1'
    if dest.exists():raise ValueError('Existing combined analysis must not be overwritten')
    paths={3:ROOT/'full_l3_batch.json',4:ROOT/'full_mfm_l4_v1'/'batch.json'}
    batches={level:json.loads(path.read_text()) for level,path in paths.items()}
    cases={level:accept_cases(batch,level) for level,batch in batches.items()}
    if cases[3][0]['physics']!=cases[4][0]['physics'] or cases[3][0]['binary_sha256']!=cases[4][0]['binary_sha256']:
        raise ValueError('Cross-level physical metadata/binary differ')
    inputs={level:params((Path(cases[level][0]['directory'])/'params.txt').read_text()) for level in (3,4)}
    changes={k for k in inputs[3] if inputs[3][k]!=inputs[4][k]}
    allowed={'MaxMemSize',*[f'Softening_Type{i}' for i in range(6)]}
    if set(inputs[3])!=set(inputs[4]) or changes!=allowed:raise ValueError('Unreviewed cross-level parameter difference')
    for i in range(6):
        if float(inputs[4][f'Softening_Type{i}'])!=float(inputs[3][f'Softening_Type{i}'])/2:raise ValueError('Wrong resolution-scaled softening')
    results=[];levels=[]
    for level in (3,4):
        for case in cases[level]:results.append(verify_case(case))
        levels.append(dict(level=level,initial_elements_per_radius=(8*2**level)/20,
            **pair_metric(*[c['series'] for c in cases[level]])))
    report=dict(status='share_with_caveats',code='GIZMO MFM',controls=4,new_level4_controls=2,
        chi=cases[3][0]['physics']['chi'],mach=cases[3][0]['physics']['mach'],levels=levels,cases=results,
        native_states=sum(len(c['series']) for c in results),
        source_batches=[dict(level=l,path=str(paths[l]),sha256=sha(paths[l])) for l in (3,4)],
        analysis_sha256=sha(__file__),cross_level_parameter_changes=sorted(changes),
        metric='rho > rho_cloud_initial/3; same measured initial dense mass within each pair. Each resolution has its own measured initial denominator. Curves use every actual header time; scalar peak uses linear interpolation onto0:0.05:5 t_cc.',
        caveats=['Only two coarse levels (3.2/6.4 initial elements per cloud radius), not demonstrated convergence or universal historical reuse.',
            'Original fully periodic boundaries and native kernel pressure/density deviations retained; not a matched grid inflow/outflow experiment.',
            'No passive material tracer or all-material-retained terminal-image claim. Conserved output velocity remains staggered.',
            'MFV L3 failures are excluded from this method-specific result and separately retained as failed controls.',
            'No snapshots retimed, repeated, deleted or substituted; independent yt evidence covers every accepted native state.'])
    if report['native_states']!=404:raise ValueError('Unexpected total native output count; review rather than filter')
    dest.mkdir()
    fig,ax=plt.subplots(figsize=(9,5.4),layout='constrained')
    for c in results:
        level=c['level'];law='sharp' if c['mode']==0 else 'historical tanh'
        ax.plot([r['t_over_tcc'] for r in c['series']],[r['dense_mass_over_initial'] for r in c['series']],
            color={3:'#0072B2',4:'#D55E00'}[level],ls='-' if c['mode']==0 else '--',
            lw=1.9,label=f'L{level}, {law}')
    upper=max(1.05,max(r['dense_mass_over_initial'] for c in results for r in c['series'])*1.05)
    ax.set(title='Native GIZMO MFM | chi=100, Mach 2\nTwo coarse resolutions; original periodic boundaries',
        xlabel=r'$t/t_{cc}$',ylabel='Dense mass / initial dense mass at that resolution',xlim=(0,5),ylim=(0,upper))
    ax.grid(alpha=.2);ax.spines[['top','right']].set_visible(False);ax.legend(loc='lower left',ncol=2)
    fig.savefig(dest/'mass_mfm_L3_L4.png',dpi=180);plt.close(fig)
    report['plot_sha256']=sha(dest/'mass_mfm_L3_L4.png');save(dest/'report.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2),flush=True)

if __name__=='__main__':main()
