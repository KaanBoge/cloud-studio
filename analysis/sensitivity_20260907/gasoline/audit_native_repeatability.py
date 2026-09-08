"""Report native repeat variation and output observations, without changing tolerances."""
import json
import itertools
import numpy as np
import gasoline_controls as g
import verify_instrumentation_v3 as v
from audit_instrumentation_differences import compare

OUT=g.ROOT/'repeatability_audit_v1'

def main():
    if OUT.exists():raise FileExistsError(OUT)
    OUT.mkdir()
    # Independent-reader caches belong to this audit, never to native inputs.
    v.OUT=OUT
    prior=json.loads((g.ROOT/'validation_v3/partial_report.json').read_text())
    assert len(prior['states'])==10
    for row in prior['states']:
        assert g.sha(row['path'])==row['sha256']
        assert max(row['independent']['relative_discrepancies'])<=1e-12
    repeat=g.ROOT/'repeatability_v1'
    batch=json.loads((repeat/'solver_batch.json').read_text())
    states=[]
    for item in batch['cases']:
        folder=repeat/item['name']
        p=g.params((folder/'run.param').read_text())
        for step in (3,6):
            path=folder/f'state.{step:06d}'
            before=g.sha(path);t,a=g.read(path)
            assert len(a)==65536 and abs(t-step*float(p['dDelta']))<5e-15
            v.iorder(path,len(a))
            mass=v.sums(a['mass'].astype(float),a['rho'].astype(float),a['metals'].astype(float))
            independent=v.independent(path,mass)
            assert g.sha(path)==before
            states.append(dict(path=str(path),sha256=before,time_code=t,independent=independent))
    baseline=[g.WORK/'original_tanh',repeat/'original_repeat1',repeat/'original_repeat2']
    comparisons=[]
    for step in (3,6):
        filename=f'state.{step:06d}'
        for a,b in itertools.combinations(baseline,2):
            comparisons.append(dict(kind='same_original_binary',first=str(a),second=str(b),
                                    snapshot=filename,fields=compare(a/filename,b/filename)))
        comparisons.append(dict(kind='same_hook_binary_off_vs_on',first=str(g.WORK/'off_tanh'),
            second=str(g.WORK/'on_tanh'),snapshot=filename,
            fields=compare(g.WORK/'off_tanh'/filename,g.WORK/'on_tanh'/filename)))
    scalar_exact=all(all(data['unequal_values']==0 for field,data in c['fields'].items()
                        if field!='vel') for c in comparisons)
    assert scalar_exact,'Native nonvelocity changes need further diagnosis'
    orig_peak=max(c['fields']['vel']['max_absolute'] for c in comparisons if c['kind']=='same_original_binary')
    hook_peak=max(c['fields']['vel']['max_absolute'] for c in comparisons if c['kind']=='same_hook_binary_off_vs_on')
    initial=[row for row in prior['states'] if row['time_code']==0]
    report=dict(status='short_native_mass_checks_passed_bitwise_velocity_equivalence_not_established',
        full_science_controls_completed=0,native_outputs_independently_checked=14,
        unchanged_original_velocity_repeat_max_absolute=orig_peak,
        same_binary_hook_off_on_velocity_max_absolute=hook_peak,
        all_compared_nonvelocity_TIPSY_fields_exact=scalar_exact,
        hook_velocity_difference_within_measured_original_repeat_range=hook_peak<=orig_peak,
        initial_states=initial,new_independent_states=states,comparisons=comparisons,
        original_validation_attempts_retained=['validation_v1','validation_v2','validation_v3'],
        next_required=['Review complete-pair retention including every native rotating checkpoint generation.',
                       'Freeze a tested full L3 mass-study runner; preserve all native actual timestamps and sidecars.',
                       'Do not claim strict bitwise equivalence or pressure/velocity-at-header-time validation.'])
    g.write_new(OUT/'report.json',report)
    print(json.dumps({k:val for k,val in report.items() if k not in ('comparisons','initial_states','new_independent_states')},indent=2))

if __name__=='__main__':main()
