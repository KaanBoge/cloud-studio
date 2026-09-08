"""Build a metadata-only public research catalog; never run or alter a solver.

Copy new custom analysis artifacts only, preserve all existing published reports,
inspect the pinned public frames tree/indexes, and generate a dated data index.
No private recordings, credentials, native binaries or raw simulation arrays.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import csv
import hashlib
import json
import math
import re
import shutil
import urllib.request
import zipfile

REPO = Path('C:/Users/kaanb/cloud-studio-repo')
PROJECT = Path('C:/Users/kaanb/CloudCrushing')
WORK = PROJECT / 'publication_20260909'
FRAMES_SHA = '7b25e3b651dafffb76716bdf0c7d778d2e441182'
BASE_SHA = 'eb7755ea1d0585082276989e0613ec2b23d775c9'
BASE = 'https://raw.githubusercontent.com/KaanBoge/cloud-studio/' + FRAMES_SHA + '/'
API = 'https://api.github.com/repos/KaanBoge/cloud-studio/'
SAFE_EXT = {'.py', '.sh', '.ps1', '.md', '.json', '.png', '.cjs'}
EXCLUDE_COMPONENTS = {'source', 'before', '__pycache__', 'legacy_before_20260907'}
SECRET = re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,}|sk-proj-[A-Za-z0-9_-]{20,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def remote_json(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'CloudStudio-research-index'})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read()
    return json.loads(payload), hashlib.sha256(payload).hexdigest()


def copy_new(src, dest):
    if dest.exists():
        return False
    payload = src.read_bytes()
    if SECRET.search(payload):
        raise ValueError('Credential-like content; manual review required: ' + str(src))
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Destination must be new; no hardlink edits or frozen report overwrites.
    with dest.open('xb') as output:
        output.write(payload)
    if sha(src) != sha(dest):
        raise ValueError('Copy hash mismatch')
    return True


def mapped_runs():
    value = (REPO/'data/densemap.js').read_text(encoding='utf-8')
    return json.loads(re.search(r'var DENSE_RUNS=(\{.*\});', value).group(1))


def collect_streaming():
    cache = WORK/'streaming_snapshot.json'
    if cache.exists():
        data = json.loads(cache.read_text(encoding='utf-8'))
        if data['frames_commit'] != FRAMES_SHA:
            raise ValueError('Wrong pinned frame snapshot')
        return data
    tree, tree_sha = remote_json(API + 'git/trees/' + FRAMES_SHA + '?recursive=1')
    if tree.get('truncated'):
        raise ValueError('Incomplete remote tree')
    blobs = {e['path']: e for e in tree['tree'] if e['type'] == 'blob'}
    mapped = mapped_runs()
    indexes = sorted(p for p in blobs if p.endswith('/index.json'))
    def inspect(path):
        record, digest = remote_json(BASE + path)
        run = path.rsplit('/', 1)[0]
        times, frames = record['times'], record['frames']
        issues = []
        if len(times) != len(frames):
            issues.append('time_frame_count_mismatch')
        if any(not isinstance(t, (int,float)) or not math.isfinite(t) for t in times):
            issues.append('invalid_timestamp')
        elif any(b <= a for a,b in zip(times, times[1:])):
            issues.append('non_strictly_increasing_times')
        paths = [run+'/'+frame for frame in frames]
        if any(p not in blobs for p in paths):
            issues.append('referenced_frame_missing_in_remote_tree')
        if run in mapped and mapped[run] != len(frames):
            issues.append('viewer_map_count_mismatch')
        if 'cool' in run:
            scientific_status = 'historical; cooling was NOT enabled'
        elif 'gal' in run:
            scientific_status = 'historical; tracking not certified'
        else:
            scientific_status = 'historical; matched-code comparability not certified'
        return dict(run_id=run, listed_in_viewer=run in mapped,
            index_frame_count=len(frames), distinct_measured_times=len(set(times)),
            first_t_tcc=times[0] if times else None,last_t_tcc=times[-1] if times else None,
            mesh_bytes=sum(blobs[p].get('size',0) for p in paths if p in blobs),
            index_url=BASE+path,index_sha256=digest,issues=issues,
            scientific_status=scientific_status)
    with ThreadPoolExecutor(max_workers=4) as pool:
        runs = list(pool.map(inspect, indexes))
    data = dict(observed_at_utc=datetime.now(timezone.utc).isoformat(),frames_commit=FRAMES_SHA,
        remote_tree_json_sha256=tree_sha,remote_file_count=len(blobs),
        remote_payload_bytes=sum(v.get('size',0) for v in blobs.values()),
        viewer_mapped_entries=len(mapped),remote_index_count=len(runs),
        listed_index_frames=sum(r['index_frame_count'] for r in runs if r['listed_in_viewer']),
        scope='Pinned remote tree + every index checked; binary mesh payloads were not downloaded or decoded.',
        missing_mapped_indexes=sorted(set(mapped)-{r['run_id'] for r in runs}),runs=runs)
    save(cache,data)
    return data


def main():
    WORK.mkdir(exist_ok=True)
    added=[]
    for area in ('sensitivity_20260907','followup_20260907','performance_20260907c'):
        source=PROJECT/area
        for src in sorted(source.rglob('*')):
            rel=src.relative_to(source)
            if not src.is_file() or src.is_symlink() or any(p in EXCLUDE_COMPONENTS for p in rel.parts):
                continue
            # Housekeeping and mutable worker handles are not scientific evidence.
            if src.suffix not in SAFE_EXT or src.stat().st_size > 5_000_000:
                continue
            if any(k in src.name.lower() for k in ('dedup','worker','storage_inventory','storage_feasibility')) or src.name=='analysis_index.md':
                continue
            dest=REPO/'analysis'/area/rel
            if copy_new(src,dest):
                added.append(dest.relative_to(REPO).as_posix())
    export=REPO/'analysis/storage_20260909'
    probe=PROJECT/'storage_inventory_20260909/compression_probe_20260908T224306Z.json'
    copy_new(probe,export/'compression_probe.json')
    copy_new(PROJECT/'storage_inventory_20260909/compression_probe_v1.py',export/'compression_probe_v1.py')
    inventory=json.loads((PROJECT/'storage_inventory_20260909/snapshot_20260908T220546_429394Z/summary.json').read_text())
    # Project categories/counts only: omit whole-machine filenames and free-space logs.
    inv=dict(observed_at_utc=inventory['finished_utc'],scope=inventory['scope'],
        roots=[dict(category=r['path'].split('/')[-1],files=r['files'],logical_bytes=r['logical_bytes'],
                    unique_inode_logical_bytes=r['unique_inode_logical_bytes']) for r in inventory['roots']],
        metadata_only=True,raw_payload_backup=False,limitations=inventory['limitations'])
    save(export/'project_storage_inventory.json',inv)
    raw=PROJECT/'native_runs/sensitivity_20260907/enzo_L5_velocity_pair_v1'
    batch=json.loads((raw/'full_batch.json').read_text())
    progress=dict(observed_at_utc=datetime.now(timezone.utc).isoformat(),
        status=batch['status'],active_mode=batch.get('active_mode'),
        validated_new_controls=batch.get('new_full_controls',0),plan_sha256=batch['plan_sha256'],
        independently_checked_finished_cases=len(batch.get('finished',[])),
        scope='Dated launcher observation, not a live dashboard or acceptance/publication of L5 results.')
    save(REPO/'analysis/publication_20260909/enzo_l5_observation.json',progress)
    for case in batch.get('finished',[]):
        if case['status']!='complete_independent_checks':
            raise ValueError('Unexpected finished case status')
        name='sharp13' if case['mode']==0 else 'tanh13'
        src=raw/'full'/name/'result.json'
        copy_new(src,REPO/'analysis/sensitivity_20260907/enzo/l5_direct_v1'/('native_check_'+name+'.json'))
    copy_new(raw/'diagnostics_batch.json',REPO/'analysis/sensitivity_20260907/enzo/l5_direct_v1/diagnostics_batch.json')
    streaming=collect_streaming()
    save(REPO/'data/streaming-inventory.json',streaming)
    with (REPO/'data/streaming-inventory.csv').open('w',newline='',encoding='utf-8') as f:
        keys=('run_id','listed_in_viewer','index_frame_count','distinct_measured_times','first_t_tcc','last_t_tcc','mesh_bytes','scientific_status','index_url','issues')
        writer=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore');writer.writeheader()
        for row in streaming['runs']:
            writer.writerow(dict(row,issues='; '.join(row['issues'])))
    for name in ('build_research_index.py','validate_publication.py'):
        src=WORK/name
        if src.exists():
            dest=REPO/'analysis/publication_20260909'/name
            # This current publication builder is mutable until its first commit;
            # it is not part of any frozen experiment.
            if dest.exists():dest.write_bytes(src.read_bytes())
            else:copy_new(src,dest)
    # Catalog contents already selected for the public repository, not arbitrary PC files.
    artifacts=[]
    for path in sorted((REPO/'analysis').rglob('*')):
        if path.is_file():
            rel=path.relative_to(REPO).as_posix()
            artifacts.append(dict(path=rel,bytes=path.stat().st_size,sha256=sha(path),kind=path.suffix.lstrip('.')))
    save(REPO/'data/research-files.json',dict(generated_at_utc=datetime.now(timezone.utc).isoformat(),
        count=len(artifacts),bytes=sum(x['bytes'] for x in artifacts),scope='Public analysis files only',files=artifacts))
    with (REPO/'data/research-files.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=('path','bytes','sha256','kind'));writer.writeheader();writer.writerows(artifacts)
    summary=json.loads((REPO/'analysis/sensitivity_20260907/resolution_summary_v2/summary.json').read_text())
    site=dict(generated_at_utc=datetime.now(timezone.utc).isoformat(),
        accepted_controls=summary['accepted_full_controls'],accepted_pairs=summary['accepted_pairs'],
        analyzed_native_states=summary['native_states_in_accepted_analysis'],
        historical_viewer_entries=streaming['viewer_mapped_entries'],
        historical_indexed_frames=streaming['listed_index_frames'],analysis_files=len(artifacts),
        analysis_bytes=sum(x['bytes'] for x in artifacts),frames_commit=FRAMES_SHA,
        new_enzo_l5=progress,summary_source='analysis/sensitivity_20260907/resolution_summary_v2/summary.json')
    save(REPO/'data/research-status.json',site)
    download=REPO/'downloads/research-evidence-2026-09-09.zip';download.parent.mkdir(exist_ok=True)
    excluded=[]
    with zipfile.ZipFile(download,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as archive:
        for item in artifacts:
            path=Path(item['path'])
            if any(x in EXCLUDE_COMPONENTS for x in path.parts) or path.suffix not in SAFE_EXT:
                excluded.append(item['path']);continue
            archive.write(REPO/path,item['path'])
        for path in sorted((REPO/'docs').rglob('*')):
            if path.is_file():archive.write(path,path.relative_to(REPO).as_posix())
        for name in ('research-files.json','research-files.csv','research-status.json','streaming-inventory.json','streaming-inventory.csv'):
            archive.write(REPO/'data'/name,'data/'+name)
    if download.stat().st_size>=90*1024**2:
        raise ValueError('Evidence download exceeds conservative per-file budget')
    save(WORK/'build_receipt.json',dict(base_commit=BASE_SHA,added_analysis_files=added,
        download_bytes=download.stat().st_size,download_sha256=sha(download),
        archive_excluded=excluded,artifact_count=len(artifacts),status=site))
    print(json.dumps(dict(new_custom_artifacts=len(added),download_MB=download.stat().st_size/1e6,
        historical_viewer_entries=site['historical_viewer_entries'],indexed_frames=site['historical_indexed_frames'],
        analysis_files=len(artifacts),analysis_MB=site['analysis_bytes']/1e6,
        missing_indexes=streaming['missing_mapped_indexes'],index_issues=[r['run_id'] for r in streaming['runs'] if r['issues']])))


if __name__=='__main__':main()
