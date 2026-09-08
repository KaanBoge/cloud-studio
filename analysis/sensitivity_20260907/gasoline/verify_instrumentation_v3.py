"""Validate all native short outputs without modifying or resimulating them."""
import json
from pathlib import Path
import sys
import numpy as np
import gasoline_controls as g

OUT=g.ROOT/'validation_v3'


def sidecar(path):
    with Path(path).open() as f:
        n=int(f.readline().strip())
        a=np.loadtxt(f,dtype=np.float64)
    if a.shape != (n,) or not np.isfinite(a).all():
        raise ValueError('Invalid native sidecar '+str(path))
    return a


def iorder(path,n):
    a=sidecar(str(path)+'.iord')
    if len(a)!=n or not np.array_equal(np.sort(a),np.arange(n)):
        raise ValueError('iOrder not a complete native IC-index permutation')
    return a.astype(np.int64)


def sums(m,rho,metals):
    # Explicit study chi from the pinned generation manifest, not a new CLI value.
    chi=json.loads((g.WORK/'preparation.json').read_text())['chi']
    return [float(m.sum(dtype=np.float64)),
            float(m[rho>chi/3].sum(dtype=np.float64)),
            float((m*metals).sum(dtype=np.float64))]


def independent(path,direct):
    from yt.frontends.tipsy.api import TipsyDataset
    ds=TipsyDataset(str(path),parameter_file=str(path.parent/'run.param'),
        bounding_box=[[-10,10],[-5,5],[-5,5]],
        index_filename=str(OUT/(path.parent.name+'_'+path.name+'.index5')),
        kdtree_filename=str(OUT/(path.parent.name+'_'+path.name+'.kdtree')))
    # Raw particle sums only. No spatial reconstruction or change of native BCs.
    ds._periodicity=(False,False,False)
    ad=ds.all_data()
    m=ad['Gas','Mass'].to_value('code_mass').astype(np.float64)
    rho=ad['Gas','Density'].to_value('code_mass/code_length**3').astype(np.float64)
    metal=ad['Gas','Metals'].to_value('').astype(np.float64)
    measured=sums(m,rho,metal)
    rel=[abs(a-b)/max(abs(a),1) for a,b in zip(direct,measured)]
    if max(rel)>1e-12:
        raise ValueError('Independent mass discrepancy '+str(rel))
    return dict(reader='yt TipsyDataset raw fields',mass_sums=measured,
                relative_discrepancies=rel,count=len(m))


def verify():
    if OUT.exists():
        raise FileExistsError('Do not overwrite an existing validation attempt')
    OUT.mkdir()
    report=dict(status='checking',full_science_controls_completed=0,states=[],
                equivalence=[],initial_pair={},limitations=[
                'Only six original-size native timesteps, not a full trajectory equivalence proof.',
                'Original fully periodic, equal-volume variable-mass SPH recipe; not a grid-code baseline.',
                'TIPSY temp uses parameter-derived energy scaling, not an assumed physical Kelvin field.',
                'Mass/color sums cannot certify no periodic boundary crossing.',
                'Evolved .pres is cached from predictor-energy force evaluation; TIPSY temp stores u after the closing kick. These are not the same-stage pressure diagnostic.',
                'Pressure-at-header-time and evolved velocity synchronization remain uncertified; mass diagnostics only.'])
    try:
        batch=json.loads((g.WORK/'solver_batch.json').read_text())
        assert batch['status']=='native_short_tests_finished_not_yet_validated'
        arrays={}
        prep=json.loads((g.WORK/'preparation.json').read_text())
        for case in prep['cases']:
            folder=g.WORK/case['name']
            p=g.params((folder/'run.param').read_text())
            assert g.sha(folder/'run.param')==case['parameter_sha256']
            expected={'state.000003':3*float(p['dDelta']),
                      'state.000006':6*float(p['dDelta'])}
            if case['hook']:expected['state.initial']=0.
            actual={x.name for x in folder.iterdir() if x.is_file() and
                    (x.name=='state.initial' or (x.name.startswith('state.') and x.name[6:].isdigit()))}
            assert actual==set(expected),(actual,expected)
            for name,want in sorted(expected.items(),key=lambda x:x[1]):
                path=folder/name
                before=g.sha(path)
                t,a=g.read(path)
                assert len(a)==65536
                assert abs(t-want)<5e-15,(t,want)
                ids=iorder(path,len(a))
                u=a['temp'].astype(np.float64)*g.energy_factor(p)
                rho=a['rho'].astype(np.float64)
                pressure=(float(p['dConstGamma'])-1)*rho*u
                native_pres=sidecar(str(path)+'.pres')
                assert (native_pres>0).all()
                relative=float(np.max(np.abs(native_pres-pressure)/pressure))
                # pkdGasPressure uses uPred; msrTopStepKDK then closes its kick
                # before writing TIPSY p->u. Do not equate these evolved fields.
                # At initialization uPred==u, so the original precision check
                # remains mandatory, unchanged, for each native initial state.
                if name=='state.initial' and relative>8*np.finfo(np.float32).eps:
                    raise ValueError('Initial native pressure recovery mismatch '+str(relative))
                mass=sums(a['mass'].astype(np.float64),rho,a['metals'].astype(np.float64))
                row=dict(case=case['name'],path=str(path),sha256=before,time_code=t,
                         time_tcc=t/(np.sqrt(prep['chi'])*prep['radius']/prep['vwind']),
                         count=len(a),mass_sums=mass,pressure_min=float(pressure.min()),
                         pressure_max=float(pressure.max()),native_pressure_relative_difference=relative,
                         pressure_comparison='same-stage initial check' if name=='state.initial' else 'different native stages; not an error estimate',
                         sidecars={f.name:g.sha(f) for f in sorted(folder.glob(name+'.*'))},
                         independent=independent(path,mass))
                assert g.sha(path)==before
                report['states'].append(row)
                arrays[(case['name'],name)]=a[np.argsort(ids)]
                if name=='state.initial':
                    ic=g.read(folder/'ic.std')[1]
                    ordered=arrays[(case['name'],name)]
                    for key in ('pos','mass','vel','temp','metals'):
                        assert np.array_equal(ordered[key],ic[key]),('native initial differs from IC',key)
                    row['initial_density_vs_analytic_relative_max']=float(np.max(
                        abs(ordered['rho'].astype(np.float64)/ic['rho']-1)))
                print('checked',case['name'],name,'t=',t,flush=True)
        # No timestamp renaming, field normalization or selective omission in comparison.
        for other in ('off_tanh','on_tanh'):
            for name in ('state.000003','state.000006'):
                ref=arrays[('original_tanh',name)]
                new=arrays[(other,name)]
                for key in g.GAS.names:
                    assert np.array_equal(ref[key],new[key]),('evolved field changed',other,name,key)
                a=g.WORK/'original_tanh';b=g.WORK/other
                sides={p.name for p in a.glob(name+'.*')}
                assert sides=={p.name for p in b.glob(name+'.*')}
                for suffix in sides:
                    assert (a/suffix).read_bytes()==(b/suffix).read_bytes(),('sidecar changed',other,suffix)
                report['equivalence'].append(dict(reference='original_tanh',other=other,
                    snapshot=name,all_native_fields_exact=True,all_sidecar_bytes_exact=True))
        historical=arrays[('on_tanh','state.initial')]
        sharp=arrays[('on_sharp','state.initial')]
        for key in g.GAS.names:
            if key!='vel':assert np.array_equal(historical[key],sharp[key]),('paired initial field',key)
        report['initial_pair']=dict(nonvelocity_native_fields_exact=True,
            velocity_matches_corresponding_IC_exact=True,
            fixed_initial_dense_mass=sums(historical['mass'].astype(float),
              historical['rho'].astype(float),historical['metals'].astype(float))[1])
        report['status']='passed_native_L3_short_output_equivalence_and_mass_checks'
        report['native_output_count']=len(report['states'])
        report['solver_results']=batch['cases']
        report['retained_bytes']=sum(p.stat().st_size for p in g.WORK.rglob('*') if p.is_file())
        g.write_new(OUT/'report.json',report)
        return report
    except Exception as exc:
        report.update(status='validation_needs_review',error=repr(exc))
        g.write_new(OUT/'partial_report.json',report)
        raise


if __name__=='__main__':
    print(json.dumps(verify(),indent=2))
