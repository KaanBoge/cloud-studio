import json
from analyze_flashx import independent
from run_flashx import ROOT,save

def main():
    batch=json.loads((ROOT/'smoke_batch.json').read_text());checks=[]
    for case in batch['finished']:
        for row in case['series']:
            checks.append(dict(snapshot=row['snapshot'],relative_mass_error=independent(row,case['parameters'])))
    report=dict(status='passed',independent_reader='yt FLASH frontend',checks=checks)
    save(ROOT/'yt_smoke_validation.json',report);print(json.dumps(report),flush=True)

if __name__=='__main__':main()
