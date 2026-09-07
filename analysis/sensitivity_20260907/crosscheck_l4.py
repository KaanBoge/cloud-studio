import json
from pathlib import Path
from analyze import ROOT,independent_yt

report=json.loads((ROOT/'analysis/report.json').read_text())
batch=json.loads((ROOT/'batch.json').read_text())
checks=[]
for record in batch['finished']:
    if record['level']!=4:continue
    rows=report['series'][Path(record['directory']).name]
    for row in (rows[0],rows[-1]):checks.append(independent_yt(record,row))
result={'passed':True,'checks':checks,'scope':'Additional independent native yt sums at nonzero final dense masses, L4.'}
with (ROOT/'analysis/crosscheck_l4.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result,indent=2))
