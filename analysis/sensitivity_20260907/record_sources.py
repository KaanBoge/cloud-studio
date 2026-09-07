"""Record the actual on-disk historical laws used for this pilot."""
import json
from pathlib import Path
from build import ROOT,sha
sources={
 'athpp_historical_tanh':'/home/kaan/codes/athenapp/src/pgen/cloud_wind.cpp.tanh_backup',
 'apk_historical_momentum':'/mnt/c/Users/kaanb/CloudCrushing/audit_20260907/before/home/kaan/codes/athenapk/src/pgen/cloud.cpp',
 'athpp_production_source':'/home/kaan/codes/athenapp/src/pgen/cloud_wind.cpp',
 'apk_production_source':'/home/kaan/codes/athenapk/src/pgen/cloud.cpp'}
rows={}
for name,path in sources.items():
    lines=Path(path).read_text().splitlines()
    rows[name]=dict(path=path,sha256=sha(path),velocity_lines=[dict(line=i+1,text=s)
        for i,s in enumerate(lines) if any(w in s for w in ('Real fv','Real vx','mom =','if (rad >'))])
(ROOT/'historical_sources.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(rows,indent=2))
