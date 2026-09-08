"""Native-time mass curves for the validated repaired MFV L3 pair only."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path('/home/kaan/sensitivity_20260907/gizmo/mfv_timestep_repair_v1')
REPORT=ROOT/'sharp_full_native_v1/pair_validation.json'
DEST=ROOT/'sharp_pair_plot_v1'


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    if DEST.exists():raise ValueError('Existing plot directory; do not overwrite')
    digest=sha(REPORT);r=json.loads(REPORT.read_text())
    if r['status']!='passed_repaired_mfv_L3_pair':raise ValueError('Pair is not validated')
    comparison=r['mass_comparison'];denom=comparison['initial_dense_mass']
    for law,key in (('sharp','sharp_outputs'),('historical','historical_outputs')):
        rows=r[key];series=comparison['series'][law]
        if len(rows)<101 or len(series['native_times_tcc'])!=len(rows):raise ValueError('Missing native states')
        expected=[x['dense_mass']/denom for x in rows]
        if expected!=series['dense_mass_fraction']:raise ValueError('Plotted values differ from validated native sums')
        for row in rows:
            if sha(row['path'])!=row['sha256']:raise ValueError('Native state changed before plotting')
    DEST.mkdir();plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(figsize=(9,5.2))
    for law,label,color,style in (('historical','Historical tanh velocity','#0072B2','--'),('sharp','Sharp velocity boundary','#D55E00','-')):
        s=comparison['series'][law]
        ax.plot(s['native_times_tcc'],s['dense_mass_fraction'],label=label,color=color,linestyle=style,linewidth=2)
    ax.set(xlim=(0,5),ylim=(0,max(1.05,1.05*max(max(s['dense_mass_fraction']) for s in comparison['series'].values()))),
        xlabel=r'$t/t_{\rm cc}$',ylabel=r'$M(\rho>\rho_{\rm cloud,0}/3)/M_{\rm dense}(0)$',
        title='Repaired GIZMO MFV: velocity-prescription sensitivity\nLevel 3, initial 64 x 32 x 32 lattice; chi = 100, Mach = 2')
    ax.legend(loc='best');ax.grid(alpha=.18)
    counts=f"{len(r['historical_outputs'])} historical and {len(r['sharp_outputs'])} sharp native states; same initial denominator."
    fig.text(.12,.035,counts+'\nOne coarse resolution, not convergence or an exact-solution error estimate.',fontsize=9)
    fig.tight_layout(rect=(0,.1,1,1));target=DEST/'mass_mfv_repaired_L3.png';fig.savefig(target,dpi=160);plt.close(fig)
    if sha(REPORT)!=digest:raise ValueError('Report changed during plot')
    manifest=dict(status='rendered_pending_visual_review',report_sha256=digest,script_sha256=sha(__file__),
        plot_sha256=sha(target),native_frames=len(r['historical_outputs'])+len(r['sharp_outputs']),scope='Two mass curves at native times, not a3Dviewer export.')
    with (DEST/'manifest.json').open('x') as f:json.dump(manifest,f,indent=2,allow_nan=False)
    print(json.dumps(manifest))


if __name__=='__main__':main()
