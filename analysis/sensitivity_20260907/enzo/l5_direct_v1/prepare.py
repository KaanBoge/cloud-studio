"""Stage fresh L5 inputs and hash pins. Does not launch a native solver."""
import json
from pathlib import Path
import shutil
import sys
import runner as r


def main():
    locks=r.acquire_locks()
    r.require(not r.RAW.exists() and not (r.HERE/'plan.json').exists(),'Existing preparation cannot be overwritten')
    original=r.STUDY/'enzo'
    expected={'run_enzo.py':'6e0447d35ae1bdd8a2da46e93f549f67c4087c2bfd7b680ea4e1d11fa01911d6',
              'analyze_enzo.py':'3fcbfa6dcfcd98a91611498eef121cd721d1e9ef5ea4b54bd7526e656739d206'}
    for name,digest in expected.items():
        r.require(r.sha(original/name)==digest,'Native helper changed')
        r.require(not (r.HERE/name).exists(),'Existing helper copy')
        shutil.copy2(original/name,r.HERE/name)
        r.require(r.sha(r.HERE/name)==digest,'Helper copy changed bytes')
    e,_=r.helpers()
    r.require(r.sha(r.BINARY)==r.BINARY_SHA,'Native binary mismatch')
    before=r.storage(2*e.budget(5)+r.DIAGNOSTICS)
    r.RAW.mkdir(parents=True);(r.RAW/'scratch').mkdir()
    probe=r.RAW/'storage_probe.bin'
    with probe.open('xb') as stream:
        stream.write(bytes(range(256))*256);stream.flush()
        import os
        os.fsync(stream.fileno())
    paths=[r.HERE/name for name in ('runner.py','prepare.py','test_runner.py','PLAN.md',*expected)]
    paths += [r.BINARY,original/'build.json',r.GUEST/'build.json',
        Path('/home/kaan/ic_audit_20260907/grid_tests/enzo_chi100/CloudWind.enzo'),
        Path('/home/kaan/verified_20260907/storage_guard.py'),
        Path('/home/kaan/verified_20260907/run_params.py'),
        r.STUDY/'build.py',Path('/mnt/c/Users/kaanb/CloudCrushing/audit_20260907/grid_smokes.py')]
    windows={'storage_probe.bin':r.sha(probe)}
    for smoke in (True,False):
        for mode in (0,1):
            folder=r.RAW/('diagnostics' if smoke else 'full')/('tanh13' if mode else 'sharp13')
            folder.mkdir(parents=True)
            text=e.input_for(5,mode,smoke)
            target=folder/'CloudWind.enzo';target.write_text(text)
            r.require(e.no_mode(text)==e.no_mode(e.input_for(5,1-mode,smoke)),'Confounded pair')
            paths.append(target);windows[str(target.relative_to(r.RAW))]=r.sha(target)
    plan=dict(status='staged_pending_tests_and_windows_readback',case_budget_bytes=e.budget(5),
        full_pair_budget_bytes=2*e.budget(5),diagnostics_budget_bytes=r.DIAGNOSTICS,
        guest_ancillary_bytes=r.ANCILLARY,separate_reserve_bytes=r.RESERVE,
        pins={str(p):r.sha(p) for p in paths},windows_files=windows,storage=before,
        binary=str(r.BINARY),binary_sha256=r.BINARY_SHA,level=5,chi=100,mach=2,
        dimensions=[256,128,128],ranks=8,old_blanket_queue_enabled=False)
    r.save(r.HERE/'plan.json',plan)
    print(json.dumps(dict(raw=str(r.RAW),plan=str(r.HERE/'plan.json'),
                         plan_sha256=r.sha(r.HERE/'plan.json'),full_pair_gib=2*e.budget(5)/r.GIB,
                         storage=before),indent=2),flush=True)


if __name__=='__main__':main()
