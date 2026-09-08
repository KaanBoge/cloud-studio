"""Read-only checks of this publication; no native analyses or solvers executed."""
import ast
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit
import zipfile

ROOT=Path('C:/Users/kaanb/cloud-studio-repo')
WORK=Path('C:/Users/kaanb/CloudCrushing/publication_20260909')


def require(value,message):
    if not value:raise AssertionError(message)


class Links(HTMLParser):
    def __init__(self):super().__init__();self.targets=[];self.ids=[];self.scripts=[]
    def handle_starttag(self,tag,attributes):
        a=dict(attributes)
        if a.get('id'):self.ids.append(a['id'])
        for key in ('href','src'):
            if a.get(key):self.targets.append(a[key])


def main():
    checks=[]
    status=json.loads((ROOT/'data/research-status.json').read_text())
    require((status['accepted_controls'],status['accepted_pairs'],status['analyzed_native_states'])==(50,25,5054),'Wrong accepted scope')
    checks.append('accepted counts and scope preserved')
    catalog=json.loads((ROOT/'data/research-files.json').read_text())
    require(catalog['count']==len(catalog['files']),'Catalog count')
    for record in catalog['files']:
        path=ROOT/record['path']
        require(path.is_file() and path.stat().st_size==record['bytes'],'Catalog file/size mismatch '+str(path))
        with path.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
        require(digest==record['sha256'],'Catalog hash mismatch '+str(path))
    checks.append('all public analysis catalog sizes and SHA-256 hashes match')
    streams=json.loads((ROOT/'data/streaming-inventory.json').read_text())
    require(not streams['missing_mapped_indexes'],'Viewer indexes missing')
    require(all(not run['issues'] for run in streams['runs']),'Remote index integrity issues')
    require(streams['viewer_mapped_entries']==sum(r['listed_in_viewer'] for r in streams['runs']),'Viewer count mismatch')
    require(status['historical_indexed_frames']==sum(r['index_frame_count'] for r in streams['runs'] if r['listed_in_viewer']),'Frame count mismatch')
    checks.append('every pinned remote index has valid times and existing frame references')
    targets=[]
    for name in ('research.html','index.html','viewer.html'):
        parser=Links();parser.feed((ROOT/name).read_text(encoding='utf-8'))
        require(len(parser.ids)==len(set(parser.ids)),'Duplicate element ID '+name)
        if name=='research.html':targets.extend((ROOT/name,url) for url in parser.targets)
    for name in ('README.md','CONTRIBUTING.md','docs/DATA.md','docs/METHODS.md','docs/ROADMAP.md','docs/UPDATES.md','analysis/storage_20260909/README.md'):
        text=(ROOT/name).read_text(encoding='utf-8')
        targets.extend((ROOT/name,m.group(1)) for m in re.finditer(r'\[[^\]]*\]\(([^)]+)\)',text))
    for source,url in targets:
        split=urlsplit(url)
        if split.scheme or url.startswith('#'):continue
        path=(source.parent/unquote(split.path)).resolve()
        require(path.is_relative_to(ROOT) and path.exists(),'Missing/escaped local link '+str(path))
    checks.append('all new guide and research-page local links resolve; HTML IDs unique')
    for path in (ROOT/'analysis/sensitivity_20260907/enzo/l5_direct_v1').glob('*.py'):
        ast.parse(path.read_text(encoding='utf-8-sig'),filename=str(path))
    for name in ('build_research_index.py','validate_publication.py'):
        ast.parse((ROOT/'analysis/publication_20260909'/name).read_text(encoding='utf-8-sig'))
    result=subprocess.run(['node','--check',str(ROOT/'research.js')],capture_output=True,text=True)
    require(result.returncode==0,'Research JS syntax error '+result.stderr)
    checks.append('new JavaScript and Enzo/publication Python syntax checks pass')
    path=ROOT/'downloads/research-evidence-2026-09-09.zip'
    with zipfile.ZipFile(path) as z:
        require(z.testzip() is None,'Archive CRC failure')
        require(all(not n.startswith('/') and '..' not in Path(n).parts for n in z.namelist()),'Unsafe ZIP member')
        require('docs/DATA.md' in z.namelist(),'Missing archive guide')
    checks.append('evidence ZIP decompresses with valid CRC and safe paths')
    total=sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.relative_to(ROOT).parts)
    require(total<970_000_000,'Conservative published-site size budget exceeded')
    require(path.stat().st_size<90*1024**2,'Archive exceeds per-file budget')
    checks.append('site and archive below conservative GitHub budgets')
    proof=dict(status='passed_static_publication_checks',checks=checks,
        site_bytes=total,archive_bytes=path.stat().st_size,analysis_files=catalog['count'],
        historical_viewer_entries=streams['viewer_mapped_entries'],indexed_frames=status['historical_indexed_frames'],
        limitations=['No browser visual QA requested or performed.','Native solver validation is separate.','Remote mesh payloads not decoded; only their tree entries and indexes checked.'])
    (WORK/'validation.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(proof))


if __name__=='__main__':main()
