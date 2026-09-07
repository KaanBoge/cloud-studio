"""Real native invalid-mode test. Preserves input and failure logs."""
import json
import subprocess
from run_flash import ROOT,input_for,save

def main():
    folder=ROOT/'invalid_mode';folder.mkdir(exist_ok=False)
    (folder/'flash.par').write_text(input_for(3,0,True).replace('sim_velocityIC = 0','sim_velocityIC = 2'))
    with (folder/'run.log').open('x') as log:
        r=subprocess.run(['mpirun','--bind-to','core','-np','8',str(ROOT/'flash4_pair')],cwd=folder,
            stdout=log,stderr=subprocess.STDOUT,timeout=90)
    if r.returncode==0 or list(folder.glob('*hdf5*')) or 'sim_velocityIC must be 0 or 1' not in (folder/'run.log').read_text():
        raise ValueError('Native invalid mode was not rejected before output')
    report=dict(status='passed',native_invalid_mode_rejected=True,returncode=r.returncode,directory=str(folder))
    save(ROOT/'setup_validation.json',report);print(json.dumps(report),flush=True)

if __name__=='__main__':main()
