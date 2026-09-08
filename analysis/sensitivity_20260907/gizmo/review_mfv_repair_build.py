"""Read-only review of new isolated builds: ABI/toolchain/source, no evolution."""
import json
from pathlib import Path
import re
import subprocess

import diagnose_mfv_restart as decoder
from build_mfv_repair import ROOT, CANON, sha, require


def main():
    target=ROOT/'build_review.json'
    require(not target.exists(), 'Existing build review')
    require(sha(decoder.__file__)=='df5a3f097c7f4c6cdd04d80036316f99e202f9d7c9c46f5ab131763d71a89e94', 'Decoder changed')
    build=json.loads((ROOT/'build_report.json').read_text())
    rows={}
    selected={
        'global_data_all_processes':['Time','TimeMax','TotNumPart','TotN_gas','MinEgySpec','Timebase_interval','cf_hubble_a','cf_a3inv','BoxSize','ComovingIntegrationOn'],
        'particle_data':['Type','ID','ID_child_number','ID_generation','Pos','Mass','Vel','GravAccel'],
        'gas_cell_data':['Density','MassTrue','dMass','DtMass','ParticleVel','Pressure','InternalEnergy','InternalEnergyPred','DtInternalEnergy'],
    }
    old_types=None
    old_producers=None
    for label,path in [('original',ROOT.parent/'GIZMO_mfv_pair')]+[(k,Path(v['path'])) for k,v in build['binaries'].items()]:
        expected='b7634f844d98ceef246d66e2243827f0c5774c9997b92bd8ffeedfdf940eed91' if label=='original' else build['binaries'][label]['sha256']
        require(sha(path)==expected, 'Changed binary '+label)
        dies=decoder.parse_dwarf(subprocess.check_output(['readelf','--debug-dump=info',str(path)],text=True))
        types,layout=decoder.layouts(dies,selected)
        producers=sorted(set(d['attrs']['producer'].rsplit('): ',1)[-1]
            for d in dies.values() if d['tag']=='DW_TAG_compile_unit'))
        if label=='original':old_types,old_producers=types,producers
        require(all(types[k]==old_types[k] for k in selected), 'Selected native ABI changed')
        require(producers==old_producers, 'Recorded compiler/options differ from original')
        asm=subprocess.check_output(['objdump','-d','--disassemble=set_fast_math',str(path)],text=True)
        require('0x8040' in asm and 'ldmxcsr' in asm, 'Expected native fast-math constructor missing')
        rows[label]=dict(path=str(path),sha256=expected,selected_abi=layout,
            dwarf_producers=producers,fast_math_constructor=asm,
            note='Constructor instructions checked; not a new dynamic FTZ observation or full restart-executability test.')
    manifest=json.loads((ROOT/'source_manifest.json').read_text())
    for entry in manifest['source_files']:
        require(sha(CANON/entry['path'])==entry['sha256'],'Canonical source changed')
    mfm=(ROOT/'mfm_probe.i').read_text()
    start=mfm.index('int hydro_force_evaluate(int target')
    # Keep this limited to the actual function definition, not later toplevel code.
    start=mfm.index('int hydro_force_evaluate(int target',start+1) if ';' in mfm[start:mfm.index('{',start)] else start
    opening=mfm.index('{',start); depth=1; end=opening+1
    while depth and end<len(mfm):
        depth+=(mfm[end]=='{')-(mfm[end]=='}');end+=1
    require(depth==0,'Cannot delimit native preprocessed MFM function')
    body=mfm[start:end]
    uses=[line.strip() for line in body.splitlines() if re.search(r'\bdt_hydrostep(?:_i)?\b',line)]
    require(len(uses)==2 and 'double hinv_i' in uses[0] and 'dt_hydrostep = DMAX' in uses[1],
            'Unexpected active MFM local timestep consumer')
    report=dict(status='passed_selected_abi_toolchain_and_source_review_not_native_evolution',
        build_report_sha256=sha(ROOT/'build_report.json'),script_sha256=sha(__file__),
        decoder_sha256=sha(decoder.__file__),binaries=rows,mfm_active_local_timestep_lines=uses,
        mfm_limit='In this exact preprocessed configuration, the uninitialized local only feeds an unused maximum; optional half-step/upwind/MFV mass branches absent. No all-configuration claim or MFM rerun.',
        native_simulations_started=0,canonical_source_files_changed=0)
    with target.open('x') as stream:json.dump(report,stream,indent=2)
    print(json.dumps(dict(status=report['status'],report_sha256=sha(target),native_simulations_started=0)))


if __name__=='__main__':main()
