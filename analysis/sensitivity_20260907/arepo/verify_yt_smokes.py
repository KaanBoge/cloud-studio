"""Independent native particle sums with explicit rectangular bounding box."""
import gc,json
from pathlib import Path
import numpy as np
import yt
from yt.frontends.arepo.api import ArepoHDF5Dataset
from run_arepo import ROOT,save,raw,sha
yt.set_log_level(40)

def check(row,p):
    bounds=np.array([p['domain_left'],p['domain_right']]).T
    before=sha(row['snapshot'])
    # Public Arepo lacks the old VORONOI Config marker used by yt auto-detection.
    # Select its native frontend explicitly, instead of Gadget SPH reconstruction.
    ds=ArepoHDF5Dataset(row['snapshot'],bounding_box=bounds);ad=ds.all_data()
    mass=ad['PartType0','Masses'].to_value('code_mass')
    rho=ad['PartType0','Density'].to_value('code_density')
    tracer=np.asarray(ad['PartType0','PassiveScalars']).reshape(-1)
    if len(mass)!=row['elements'] or abs(float(ds.current_time.to_value('code_time'))-row['time_code'])>1e-12:raise ValueError('yt drops native particles or changes time')
    measured=dict(total_mass=float(mass.sum()),dense_mass=float(mass[rho>p['rho_wind']*p['chi']/3].sum()),tracer_mass=float((mass*tracer).sum()))
    errors={k:abs(v-row[k])/max(abs(row[k]),1e-12) for k,v in measured.items()}
    if max(errors.values())>1e-11:raise ValueError('yt native mass cross-check failed')
    if sha(row['snapshot'])!=before:raise ValueError('Native snapshot changed during independent read')
    del ad,ds;gc.collect();return errors

def main():
    batch=json.loads((ROOT/'smoke_batch_v2.json').read_text());checks=[]
    for case in batch['finished']:
        for row in case['series']:checks.append(dict(snapshot=row['snapshot'],relative_errors=check(row,case['physics'])))
    record=dict(status='passed',checks=checks,reader='ArepoHDF5Dataset selected explicitly',scope='Independent yt native particle sums, explicit 20x10x10 bounding box, input hashes unchanged; no rendered-mesh substitution. Earlier Gadget-autodetected smoothing-length sidecars remain separate and are not native snapshots.')
    save(ROOT/'yt_smoke_validation.json',record);print(json.dumps(record,indent=2))

if __name__=='__main__':main()
