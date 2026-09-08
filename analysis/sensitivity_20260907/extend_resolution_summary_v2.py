"""Extend the immutable 23-pair summary with two newly accepted L4 pairs.

Report-only, standard-library consolidation. Never opens native outputs,
imports an old extractor, launches simulations, or overwrites an output.
"""
import copy
import hashlib
import json
import math
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEST = ROOT/'resolution_summary_v2'
OLD_SHA = '806b7a696fec08d587e78fa9a0d2d3ba1e0fce202792a51410a99d262fd9cdcf'
ADDITIONS = {
    'Gadget-4 SPH': ('gadget4/analysis_levels_v1/report.json', '6051130072ab4c50fc3712de6b449bb1951649d709288e3d55524172046bdfe3', 'series'),
    'GIZMO MFV (repaired)': ('gizmo/mfv_analysis_levels_v1/report.json', '9049de2e08bb01dc92332ff08006ad1fb4e041e80ebd65b22ab8aac50e44aefe', 'rows'),
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, value):
    with Path(path).open('x', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')


def validate_pairs(pairs):
    keys = [(p['code_id'],p['level']) for p in pairs]
    require(len(keys) == len(set(keys)), 'Duplicate native code/level pair')
    for p in pairs:
        require(p['chi'] == 100 and p['mach'] == 2 and p['level'] in (3,4,5), 'Changed scope')
        nx = 2**(p['level']+3)
        require(p['dimensions_streamwise'] == [nx,nx//2,nx//2], 'Wrong level dimensions')
        fraction = p['peak_dense_mass_separation_fraction']
        require(math.isfinite(fraction) and fraction >= 0 and p['peak_dense_mass_separation_percent'] == 100*fraction, 'Invalid metric/percentage')
        require(set(p['variants']) == {'sharp','historical'}, 'Missing or extra velocity law')
        variants = list(p['variants'].values())
        require(variants[0]['initial_dense_mass'] == variants[1]['initial_dense_mass'] > 0, 'Different paired denominator')
        for v in variants:
            require(type(v['native_states']) is int and v['native_states'] >= 2, 'Missing native states')
            # Same report-only endpoint envelope as build_resolution_summary.py:63.
            # Code-native cadence was validated upstream; never retime it here.
            require(v['first_t_over_tcc'] == 0 and math.isfinite(v['last_t_over_tcc'])
                    and 4.99 <= v['last_t_over_tcc'] <= 5.02, 'Incomplete time interval')
            require(math.isfinite(v['final_dense_fraction']) and v['final_dense_fraction'] >= 0, 'Invalid final fraction')
        require(p['reuse_decision'].startswith('undecided'), 'Unapproved reuse decision')
    return dict(accepted_pairs=len(pairs), accepted_full_controls=sum(len(p['variants']) for p in pairs),
                native_states_in_accepted_analysis=sum(v['native_states'] for p in pairs for v in p['variants'].values()))


def extend(old, additions):
    require(old['accepted_pairs'] == 23 and old['accepted_full_controls'] == 46
            and old['native_states_in_accepted_analysis'] == 4650, 'Unexpected base summary')
    require(set(additions) == set(ADDITIONS), 'Wrong new source set')
    validate_pairs(old['pairs'])
    pairs = copy.deepcopy(old['pairs'])
    for code,(source,digest,rowkey) in ADDITIONS.items():
        doc = additions[code]
        require(doc['status'] == 'share_with_caveats' and doc['controls'] == 4 and doc['new_controls'] == 2, 'New report not accepted')
        require(set(doc['cases_by_level']) == {'3','4'}, 'Unexpected resolution coverage')
        previous = [p for p in pairs if p['code'] == code and p['level'] == 3]
        require(len(previous) == 1, 'Missing unique L3 baseline')
        previous = previous[0]
        require(doc['metrics']['3']['initial_dense_mass'] == previous['variants']['sharp']['initial_dense_mass']
                and doc['metrics']['3']['peak_curve_difference_over_initial_mass'] == previous['peak_dense_mass_separation_fraction'], 'Reused L3 scalar mismatch')
        metric, cases = doc['metrics']['4'],doc['cases_by_level']['4']
        require(len(cases) == 2, 'Incomplete new pair')
        require(cases[0]['physics'] == cases[1]['physics'] and cases[0]['input_sha256'] == cases[1]['input_sha256']
                and cases[0]['binary_sha256'] == cases[1]['binary_sha256'], 'Changed within-pair recipe')
        require(cases[0]['physics']['chi'] == 100 and cases[0]['physics']['mach'] == 2, 'Wrong physical scope')
        if rowkey == 'series':
            require([c['mode'] for c in cases] == [0,1] and all(c['status'] == 'complete_independent_checks' for c in cases), 'Wrong Gadget law/status')
        else:
            require([c['law'] for c in cases] == ['sharp13','tanh13'] and all(c['status'] == 'passed_full_native_checks' for c in cases), 'Wrong MFV law/status')
        p = copy.deepcopy(previous)
        p.update(level=4, dimensions_streamwise=[128,64,64], initial_elements_per_cloud_radius=6.4,
                 peak_dense_mass_separation_fraction=metric['peak_curve_difference_over_initial_mass'],
                 peak_dense_mass_separation_percent=100*metric['peak_curve_difference_over_initial_mass'],
                 metric_source_json_pointer='/metrics/4/peak_curve_difference_over_initial_mass',
                 metric_method_verbatim=doc['metric_definition'], source_report=source,source_sha256=digest,
                 source_caveats_verbatim=doc['caveats'],variants={})
        for index,label in enumerate(('sharp','historical')):
            rows = cases[index][rowkey]
            t = [r['time_code']/cases[index]['physics']['t_cc'] for r in rows]
            require(len(rows) >= 2 and all(math.isfinite(x) for x in t) and all(a < b for a,b in zip(t,t[1:])), 'Incomplete/disordered new times')
            require(rows[0]['dense_mass'] == metric['initial_dense_mass'], 'New denominator differs')
            require(rows[-1]['dense_mass']/rows[0]['dense_mass'] == metric['final_dense_fractions'][index], 'New final fraction differs')
            p['variants'][label] = dict(source_json_pointer=f'/cases_by_level/4/{index}/{rowkey}',
                native_states=len(rows),first_t_over_tcc=t[0],last_t_over_tcc=t[-1],equal_header_intervals_retained=0,
                initial_dense_mass=metric['initial_dense_mass'],final_dense_fraction=metric['final_dense_fractions'][index])
        require(sum(len(c[rowkey]) for c in cases) == doc['new_native_states'], 'New native count mismatch')
        pairs.append(p)
    require(pairs[:23] == old['pairs'], 'Original summary entries changed')
    counts = validate_pairs(pairs)
    require(counts == dict(accepted_pairs=25,accepted_full_controls=50,native_states_in_accepted_analysis=5054), 'Unexpected combined coverage/count')
    return pairs, counts


def markdown(summary):
    pairs = summary['pairs']
    order = list(dict.fromkeys(p['code'] for p in pairs))
    lines = ['# Velocity sensitivity: updated resolution summary', '',
        '8 September 2026. **Share with the caveats below.** This summary covers 50 accepted full controls (25 velocity-law pairs) at chi=100 and Mach=2, containing 5,054 native analysis states.', '',
        'It adds the newly completed Gadget-4 and repaired MFV level-4 pairs to the [previous immutable summary](../resolution_summary_v1/README.md). No simulation or old raw analysis was rerun to make this update.', '',
        '## Peak paired dense-mass separation', '',
        'Each value is `100 * max_t |M_dense,sharp(t) - M_dense,historical(t)| / M_dense(0)`. Dense selection is rho > initial cloud density/3, with one fixed measured initial dense-mass denominator within each resolution pair. Values are percentages of initial mass, not exact-solution errors, statistical significance, or a ranking of codes.', '',
        'Source analyses use explicitly labeled linear interpolation of scalar curves onto 0:0.05:5 t_cc for the descriptive peak. All actual native frame times are retained; requested cadence does not make every native timestamp identical.', '',
        '| Native code | L3 | L4 | L5 | Accepted controls |', '| --- | ---: | ---: | ---: | ---: |']
    for code in order:
        group = [p for p in pairs if p['code'] == code]
        bylevel = {p['level']:p for p in group}
        entries = [f"[{bylevel[level]['peak_dense_mass_separation_percent']:.3f}%](../{bylevel[level]['source_report']})" if level in bylevel else 'Not tested' for level in (3,4,5)]
        lines.append('| '+code+' | '+' | '.join(entries)+f' | {2*len(group)} |')
    lines += ['| Gasoline | Validation-held | Validation-held | Not tested | 0 |', '',
        'L3 = 64 x 32 x 32 (3.2 initial elements/R); L4 = 128 x 64 x 64 (6.4/R); L5 = 256 x 128 x 128 (12.8/R). Particle/moving-mesh levels describe initial sampling, not a fixed evolved spatial resolution. L6 would be 512 x 256 x 256, not 512 cubed, and is not tested in this sensitivity summary.', '',
        '## What can and cannot be concluded', '',
        'Gadget-4 peak separation is 6.954% at L3 and 4.232% at L4; repaired MFV is 6.438% and 2.072%. Their newly completed higher-resolution controls narrow the observed paired differences, but do not establish convergence or universal insignificance.', '',
        'Athena 4.2 is 13.085%, 7.591%, then 8.695% at L3/L4/L5: even the available three-level sequence does not decline monotonically. This evidence does not justify automatically reusing or replacing every historical run, or extrapolating to different chi, Mach, numerical recipes or finer resolutions.', '',
        'AthenaPK tests its actual historical constant-outer-momentum prescription, not a tanh velocity profile. Other accepted pairs compare historical tanh velocity to sharp velocity at 1.3R. Conditions are checked within each native-code pair; pressure, boundary and tracer prescriptions are not certified identical across codes.', '',
        'A reuse decision needs a prospective scientific tolerance agreed with Ryan and provenance checks against the particular historical run. No post-hoc cutoff or code ranking is introduced. The blanket replacement queue stays inactive.', '',
        '## Essential code-specific caveats', '',
        '* The grid-code tests are coarse. Tracer losses in the finite boxes mean t=5 need not retain all cloud material. FLASH, Flash-X and Enzo-E have no native passive tracer in these recipes.',
        '* Arepo retains its periodic streamwise boundary and initial pressure deviations up to about14.45% at L3 and13.75% at L4. Moving-mesh resolution evolves.',
        '* Gadget-4 retains the existing smoothing-length seed repair and nonuniform SPH pressure: L3 peak3.9003 times nominal, L4 range0.80827 to2.10420. It is not a uniform-pressure grid baseline.',
        '* GIZMO retains periodic boundaries and small kernel-pressure deviations. Repaired MFV uses its isolated timestep repair; original failed MFV cases are excluded, not relabeled. MFM trajectories are never substituted for MFV.',
        '* Native evolved GIZMO velocities are staggered; simultaneous velocity diagnostics remain unvalidated. Particle-ID in-box mass is not a passive material-retention diagnostic, and periodic recirculation defeats a no-boundary-crossing claim.',
        '* Native resource timings are not controlled speedup/convergence benchmarks. L3/L4 storage locations can differ. Restart byte/prefix checks do not certify checkpoint resume.', '',
        'The [previous summary](../resolution_summary_v1/README.md) retains detailed source caveats for the original23 pairs. New [Gadget-4](../gadget4/analysis_levels_v1/README.md) and [MFV](../gizmo/mfv_analysis_levels_v1/README.md) reports provide their completed L3/L4 evidence. Full source caveats remain attached to each source/level in the machine-readable summary; historical one-level notes are not claims that the new L4 results are missing.', '',
        '## Remaining work and decision for Ryan', '',
        'Four Gasoline L3/L4 controls remain scientifically held: two velocity laws at each level. Its predeclared field-repeatability check failed in6/120 paired-time comparisons, including untouched-binary repeats, despite agreement in the density-selected mass diagnostic. The [force-order investigation](../gasoline/FORCE_ORDER_RESULTS.md) is completed evidence, not an unrun task. Do not silently loosen the criterion or rerun the same traces. A prospective acceptance decision and remaining same-executable sharp-IC validation are needed before full controls.', '',
        'Higher-resolution pairs remain additional storage-held work. Full raw-retention budgets and separate host/guest safety reserves must fit before launching them. No native solver was launched by this summary. All old/new raw remains retained; reports, meshes and movies are not raw backups.', '',
        'Cooling, other Mach numbers, MHD, Galilean tracking, all-material-retained Figure1 and new production3Dviewer entries are separate unvalidated scope.', '',
        '## Reproducibility and review', '',
        '[Summary JSON](summary.json) preserves25unique code/level pairs, source hashes/pointers, denominators, native-state counts and scope. [Validation](validation.json), [review](QA.md), [extension script](../extend_resolution_summary_v2.py) and [new tests](../test_resolution_summary_v2.py) document this report-only update.', '',
        'The extension script uses only the Python standard library and reads accepted scalar reports, never native output. It refuses to overwrite resolution_summary_v2. The previous23 entries are preserved exactly; two newly validated L4 entries are appended, not substituted for missing data. Every source is hash-pinned. New tests cover coverage, scope, denominator, metric/count, law and time errors.', '',
        'Native-state counts come from source records: Enzo102 per accepted case, all others101. This is not a count of auxiliary raw files. Assessment: share with caveats, not a completed all-resolution or cross-code-equivalence study.', '']
    return '\n'.join(lines)


def main():
    require(not DEST.exists(), 'Existing summary is immutable')
    old_path = ROOT/'resolution_summary_v1/summary.json'
    require(sha(old_path) == OLD_SHA, 'Base summary changed')
    old = read(old_path)
    docs, sources, proofs = {},copy.deepcopy(old['sources']),{}
    for code,(rel,digest,_) in ADDITIONS.items():
        path = ROOT/rel
        require(sha(path) == digest, 'Changed new accepted source')
        proof_path = path.parent/'publication.json'
        proof = read(proof_path)
        require(proof['status'] == 'verified_live' and any(c['path'].endswith(rel) and c['sha256'] == digest for c in proof['checks']), 'New source publication not verified')
        proofs[str(proof_path)] = sha(proof_path)
        docs[code] = read(path)
        sources[rel] = dict(sha256=digest,bytes=path.stat().st_size)
    for rel,info in sources.items():
        require((ROOT/rel).stat().st_size == info['bytes'] and sha(ROOT/rel) == info['sha256'], 'Source report changed: '+rel)
    suite = unittest.defaultTestLoader.discover(str(ROOT),pattern='test_resolution_summary_v2.py')
    tests = unittest.TextTestRunner(verbosity=2).run(suite)
    require(tests.wasSuccessful() and tests.testsRun == 12, 'New extension tests failed or missing')
    pairs,counts = extend(old,docs)
    pending = [copy.deepcopy(x) for x in old['pending_L3_L4'] if x['code'] == 'Gasoline']
    require(sum(x['controls'] for x in pending) == 4, 'Unexpected remaining scope')
    summary = dict(schema=2,generated_at_utc=datetime.now(timezone.utc).isoformat(),**counts,
        scope=old['scope'],new_native_runs=0,previous_summary_sha256=OLD_SHA,previous_pairs_reused_exactly=23,
        newly_included_pairs=2,pairs=pairs,sources=sources,publication_proof_sha256=proofs,pending_L3_L4=pending,
        pending_L3_L4_full_controls=4,higher_levels='Additional storage-held work, outside the four held Gasoline L3/L4 controls.',
        blanket_replacement_queue='inactive; not changed',verification_scope='Report-only extension. No original extractor, raw analysis or native simulation rerun.',
        extractor_sha256=sha(__file__))
    DEST.mkdir()
    save(DEST/'summary.json',summary)
    (DEST/'README.md').write_text(markdown(summary),encoding='utf-8')
    validation = dict(status='passed_report_only_extension',unit_tests_passed=tests.testsRun,
        previous_pairs_reused_exactly=23,new_pairs_checked=2,unique_code_level_pairs=counts['accepted_pairs'],
        native_states_counted_from_reports=counts['native_states_in_accepted_analysis'],new_native_runs=0,raw_files_opened=0,
        source_report_hashes_checked=len(sources),summary_sha256=sha(DEST/'summary.json'),
        readme_sha256=sha(DEST/'README.md'),test_script_sha256=sha(ROOT/'test_resolution_summary_v2.py'))
    save(DEST/'validation.json',validation)
    print(json.dumps(dict(counts=counts,validation=validation),indent=2))


if __name__ == '__main__':main()
