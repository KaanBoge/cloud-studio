'use strict';
const byId=id=>document.getElementById(id);
const number=value=>Number(value).toLocaleString('en-US');
const size=value=>value>=1e9?(value/1e9).toFixed(2)+' GB':value>=1e6?(value/1e6).toFixed(2)+' MB':(value/1e3).toFixed(1)+' KB';
function node(tag,text,className){const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(className)el.className=className;return el;}
function link(label,url){const el=node('a',label);el.href=url;return el;}
function message(tbody,text,cols){const row=node('tr'),cell=node('td',text);cell.colSpan=cols;row.append(cell);tbody.replaceChildren(row);}
async function loadJSON(path){const response=await fetch(path,{cache:'no-cache'});if(!response.ok)throw new Error('Could not load '+path);return response.json();}
async function init(){
  const results=await Promise.allSettled([loadJSON('data/research-status.json'),loadJSON('data/research-files.json'),loadJSON('data/streaming-inventory.json')]);
  if(results[0].status==='fulfilled'){
    const s=results[0].value;byId('controls').textContent=number(s.accepted_controls);byId('states').textContent=number(s.analyzed_native_states);byId('viewer-count').textContent=number(s.historical_viewer_entries);byId('files-count').textContent=number(s.analysis_files);
    byId('snapshot').textContent='Catalog snapshot: '+new Date(s.generated_at_utc).toLocaleString()+' · Not live simulation status. New Enzo L5 results are not included in the accepted summary.';
  }else byId('snapshot').textContent='Live catalog could not be loaded. The direct reports and downloads remain available.';
  if(results[1].status==='fulfilled'){
    const files=results[1].value.files;let limit=40;
    const render=()=>{const query=byId('file-search').value.trim().toLowerCase(),kind=byId('file-kind').value;const matches=files.filter(f=>(!query||f.path.toLowerCase().includes(query))&&(!kind||f.kind===kind));const rows=[];
      for(const file of matches.slice(0,limit)){const row=node('tr'),name=node('td');name.append(link(file.path.split('/').pop(),'https://github.com/KaanBoge/cloud-studio/blob/main/'+file.path),node('span',file.path,'path'));row.append(name,node('td',file.kind.toUpperCase()),node('td',size(file.bytes)));const open=node('td');open.append(link('Raw ↗',file.path));row.append(open);rows.push(row);}
      if(rows.length)byId('file-rows').replaceChildren(...rows);else message(byId('file-rows'),'No files match. Try a different code name or file type.',4);
      byId('file-result-count').textContent=number(matches.length)+' matching files';byId('more-files').hidden=matches.length<=limit;};
    byId('file-search').addEventListener('input',()=>{limit=40;render();});byId('file-kind').addEventListener('change',()=>{limit=40;render();});byId('more-files').addEventListener('click',()=>{limit+=80;render();});render();
  }else message(byId('file-rows'),'Catalog unavailable. Use the analysis CSV download above.',4);
  if(results[2].status==='fulfilled'){
    const all=results[2].value.runs;const time=t=>typeof t==='number'?Number(t.toFixed(4)).toString():'unknown';
    const render=()=>{const query=byId('run-search').value.trim().toLowerCase(),scope=byId('run-scope').value;const matches=all.filter(r=>(!query||r.run_id.toLowerCase().includes(query))&&(scope==='all'||(r.listed_in_viewer&&(scope!=='short'||r.index_frame_count<101))));const rows=[];
      for(const run of matches){const row=node('tr'),name=node('td');name.append(link(run.run_id,run.index_url));row.append(name,node('td',number(run.index_frame_count)),node('td','t = '+time(run.first_t_tcc)+' → '+time(run.last_t_tcc)),node('td',size(run.mesh_bytes)),node('td',run.scientific_status.replace('matched-code','matched code')+(run.issues.length?' · INDEX WARNING: '+run.issues.join(', '):'')));rows.push(row);}
      if(rows.length)byId('run-rows').replaceChildren(...rows);else message(byId('run-rows'),'No entries match this filter.',5);byId('run-result-count').textContent=number(matches.length)+' entries';};
    byId('run-search').addEventListener('input',render);byId('run-scope').addEventListener('change',render);render();
  }else message(byId('run-rows'),'Frame inventory unavailable. Use the frame CSV download above.',5);
}
init().catch(()=>{byId('snapshot').textContent='Catalog could not be displayed. Please use the direct report and download links.';});
