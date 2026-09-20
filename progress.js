'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const LIVE = 'https://raw.githubusercontent.com/KaanBoge/cloud-studio/live-status/progress.json';
  const REF = 'https://api.github.com/repos/KaanBoge/cloud-studio/git/ref/heads/live-status';
  let catalog, observation, remote = false, loading = false, planLimit = 60, lastRefPoll = 0, knownRef = null;
  function node(tag, text, cls) { const e=document.createElement(tag); if(text!==undefined)e.textContent=text; if(cls)e.className=cls; return e; }
  function duration(s) {
    if (s===null || s===undefined || !Number.isFinite(Number(s))) return 'Not available';
    if(s>0&&s<1)return 'Less than 1 s';
    s=Math.round(s); if(s<60)return `${s} s`;
    const h=Math.floor(s/3600),m=Math.floor(s%3600/60),sec=s%60;
    return h ? `${h} h ${m} min` : `${m} min ${sec} s`;
  }
  function grid(level) { return `${2**(level+3)} × ${2**(level+2)} × ${2**(level+2)}`; }
  function detailCell(main, sub) { const c=node('td');c.append(node('strong',main));if(sub)c.append(node('span',sub,'detail'));return c; }
  function badge(text, warning=false) { return node('span',text,'badge'+(warning?' amber':'')); }
  function option(select,value,label) { const e=node('option',label);e.value=value;$(select).append(e); }
  function stale() { return !remote || !observation || Date.now()/1000-observation.observed_unix>(observation.active?.length?180:observation.stale_after_seconds) || Date.now()/1000<observation.observed_unix-120; }
  function renderLive() {
    if(!observation)return;
    const old=stale(), active=observation.active||[], queue=observation.queue||[];
    const native=active.filter(a=>a.live&&a.phase==='Native evolution');
    $('connection').textContent=old?'Snapshot, not live':'Publisher connected';
    $('connection').className='badge'+(old?' amber':'');
    const date=new Date(observation.observed_unix*1000);
    $('updated').textContent=`Last observation ${date.toLocaleString()}. ${old?'Live activity and remaining time are withheld until a fresh report arrives.':'Display updates about every two minutes during activity. Idle reports update about every five minutes.'}`;
    $('running').textContent=old?'Unknown':String(native.length);
    $('running-note').textContent=old?'Waiting for a fresh report':active.length&&!native.length?'Validation, analysis or unconfirmed activity':'Native evolution only';
    $('queued').textContent=old?'Unknown':String(queue.length);
    const box=$('activity');box.replaceChildren();
    $('phase').textContent=old?'Last known state':active.length?active[0].phase:observation.current_state;
    $('phase').className='badge'+(old?' amber':'');
    if(!active.length){
      box.append(node('p',old?'No active run in the last report.':'No native simulation is currently active in the registered queue.','run-title'));
      box.append(node('p',observation.current_state==='Registered queue finished'?'The registered bounded queue finished. Scientific review and publication remain separate. Other planned slots are not automatically launched.':'The registered controller requires review. Other planned slots are not automatically launched.','muted'));
    }
    for(const run of active){
      box.append(node('p',`${run.code} · Level ${run.level} · ${run.law}`,'run-title'));
      box.append(node('p',`${run.dimensions} · χ = ${run.chi} · Mach ${run.mach}`,'muted'));
      const trusted=!old&&run.live, stats=node('div',undefined,'activity-grid');
      const values=[['Native progress',trusted&&run.percent!==null?`${run.percent.toFixed(1)}%`:'Unknown'],
        ['Native time remaining',trusted&&run.eta_seconds!==null?'About '+duration(run.eta_seconds):'Not estimated'],
        ['Elapsed since native start',trusted?duration(run.elapsed_seconds):'Unknown']];
      for(const [label,value] of values){const cell=node('div');cell.append(node('strong',value),node('span',label));stats.append(cell);}box.append(stats);
      if(trusted&&run.percent!==null){const bar=node('progress');bar.max=100;bar.value=run.percent;bar.setAttribute('aria-label','Native physical time progress');box.append(bar);}
      box.append(node('p','Remaining time covers native evolution only. Saved outputs still require validation and analysis.','small'));
    }
    $('queue').replaceChildren();
    if(!queue.length)$('queue').append(node('p',old?'No queued native job in the last report.':'No additional native simulation is approved and waiting to start.'));
    for(const [i,run] of queue.entries())$('queue').append(node('p',`${i+1}. ${run.code}, level ${run.level}, ${run.law}, χ = ${run.chi}, Mach ${run.mach}. ${run.status}.`));
    const m=observation.monitor||{};
    $('monitor-cost').textContent=m.collection_cpu_seconds!==undefined?`Last collector sample: ${(m.collection_cpu_seconds*1000).toFixed(1)} ms CPU · ${(m.working_set_bytes/1048576).toFixed(1)} MiB publisher RAM. Upload cost is separate.`:'Publisher measurement unavailable';
  }
  function renderRuns(){
    if(!catalog)return;
    const search=$('search').value.toLowerCase(),code=$('code').value,level=$('level').value,sort=$('sort').value;
    const rows=catalog.runs.filter(r=>(!code||r.method===code)&&(!level||r.level===Number(level))&&(!search||`${r.code} ${r.law}`.toLowerCase().includes(search)));
    rows.sort((a,b)=>sort==='slow'?b.native_seconds-a.native_seconds:sort==='level'?b.level-a.level||a.code.localeCompare(b.code):sort==='code'?a.code.localeCompare(b.code)||b.level-a.level:(Date.parse(b.finished_utc)||0)-(Date.parse(a.finished_utc)||0));
    $('runs').replaceChildren();
    for(const r of rows){const tr=node('tr');tr.append(detailCell(r.code,`${r.hardware} · ${r.law}`),detailCell(`Level ${r.level}`,grid(r.level)),
      detailCell(duration(r.native_seconds),`${(r.native_seconds/3600).toFixed(3)} hours including native output I/O`),
      detailCell(duration(r.validation_seconds),r.validation_seconds===null?'Not separately recorded':'After native evolution'),detailCell(String(r.frames),'Actual native states'),
      detailCell(r.evidence,r.review));$('runs').append(tr);}
    if(!rows.length){const tr=node('tr'),td=node('td','No completed records match these filters.');td.colSpan=6;tr.append(td);$('runs').append(tr);}
    $('shown').textContent=`${rows.length} of ${catalog.runs.length} completed controls shown. Particle grids describe initial sampling, not a fixed evolved grid.`;
  }
  function renderPlan(){
    if(!catalog)return;
    const chi=$('plan-chi').value,code=$('plan-code').value,status=$('plan-status').value;
    const slots=catalog.planning_slots.map(slot=>{const found=catalog.runs.filter(r=>r.method===slot.method&&r.level===slot.level&&r.chi===slot.chi&&r.mach===slot.mach);return found.length?{...slot,status:'Evidence available',native_runs_present:found.length,reason:'Existing controlled results require compatible scientific admission, not automatic replacement.'}:slot;});
    const rows=slots.filter(r=>(!chi||r.chi===Number(chi))&&(!code||r.method===code)&&(!status||r.status===status));
    rows.sort((a,b)=>a.code.localeCompare(b.code)||a.chi-b.chi||a.level-b.level);
    $('plan').replaceChildren();
    for(const r of rows.slice(0,planLimit)){const tr=node('tr');const readiness=node('td');readiness.append(badge(r.status,r.status!=='Evidence available'),node('span',r.reason,'detail'));
      const range=r.status==='Evidence available'?'Existing runs':r.conditional_seconds_low===null?'Uncosted':`${duration(r.conditional_seconds_low)} to ${duration(r.conditional_seconds_high)}`;
      tr.append(detailCell(r.code),detailCell(`Level ${r.level}`,r.dimensions),detailCell(`χ = ${r.chi}`,`Mach ${r.mach}`),readiness,
        detailCell(range,r.status==='Evidence available'?`${r.native_runs_present} full controls recorded`:'Planning range only, not a launch ETA'));
      $('plan').append(tr);}
    if(!rows.length){const tr=node('tr'),td=node('td','No planning slots match these filters.');td.colSpan=5;tr.append(td);$('plan').append(tr);}
    $('plan-count').textContent=`Showing ${Math.min(planLimit,rows.length)} of ${rows.length} matching slots. The full conditional inventory contains ${catalog.planning_slots.length} slots.`;
    $('more-plan').hidden=rows.length<=planLimit;
  }
  async function fetchJSON(url){const c=new AbortController(),timer=setTimeout(()=>c.abort(),12000);try{const r=await fetch(url,{signal:c.signal,cache:'no-store'});if(!r.ok)throw Error('Status unavailable');return await r.json();}finally{clearTimeout(timer);}}
  function mergeCompletions(){
    if(!catalog||!observation)return;
    let changed=false;
    for(const r of observation.completed||[]){
      if(!Number.isFinite(r.native_seconds)||!Number.isInteger(r.frames)||r.frames<90)continue;
      const existing=catalog.runs.find(e=>e.method===r.method&&e.level===r.level&&e.law===r.law&&e.chi===r.chi&&e.mach===r.mach);
      if(!existing){catalog.runs.push({...r,validation_seconds:null,finished_utc:null,evidence:'Native completion record',review:'Independent scientific review not reported',hardware:r.method==='apk'?'GPU':'CPU'});changed=true;}
    }
    if(changed){$('completed').textContent=catalog.runs.length;$('methods').textContent=new Set(catalog.runs.map(r=>r.method)).size;renderRuns();renderPlan();}
  }
  async function refresh(){
    if(loading)return; loading=true;$('refresh').disabled=true;
    try{
      if(Date.now()-lastRefPoll>=120000){
        lastRefPoll=Date.now();
        try{const ref=await fetchJSON(`${REF}?interval=${Math.floor(Date.now()/120000)}`);if(ref.ref==='refs/heads/live-status'&&/^[a-f0-9]{40}$/.test(ref.object?.sha))knownRef=ref.object.sha;}catch{knownRef=null;}
      }
      const url=knownRef?`https://raw.githubusercontent.com/KaanBoge/cloud-studio/${knownRef}/progress.json`:`${LIVE}?minute=${Math.floor(Date.now()/60000)}`;
      const data=await fetchJSON(url);if(data.schema!==1||!Array.isArray(data.active)||!Number.isFinite(data.observed_unix))throw Error('Unsupported status');
      if(!observation||data.observed_unix>=observation.observed_unix)observation=data;
      remote=true;
    }
    catch{remote=false;}
    finally{loading=false;$('refresh').disabled=false;mergeCompletions();renderLive();}
  }
  async function init(){
    try{
      [catalog,observation]=await Promise.all([fetchJSON('data/progress-catalog.json'),fetchJSON('data/progress-initial.json')]);
      if(catalog.schema!==1||!Array.isArray(catalog.runs))throw Error('Unsupported catalog');
      $('completed').textContent=catalog.runs.length;$('methods').textContent=new Set(catalog.runs.map(r=>r.method)).size;
      const codes=new Map(catalog.planning_slots.map(r=>[r.method,r.code]));
      for(const [id,name] of [...codes].sort((a,b)=>a[1].localeCompare(b[1]))){option('code',id,name);option('plan-code',id,name);}
      for(let level=1;level<=6;level++)option('level',level,`Level ${level}`);
      renderRuns();renderPlan();renderLive();await refresh();
    }catch{$('activity').replaceChildren(node('p','The inventory could not be loaded. Please refresh or use the JSON download.'));$('connection').textContent='Data unavailable';}
  }
  for(const id of ['code','level','sort','search'])$(id).addEventListener(id==='search'?'input':'change',renderRuns);
  for(const id of ['plan-chi','plan-code','plan-status'])$(id).addEventListener('change',()=>{planLimit=60;renderPlan();});
  $('more-plan').addEventListener('click',()=>{planLimit+=60;renderPlan();});$('refresh').addEventListener('click',refresh);
  setInterval(()=>{if(document.visibilityState==='visible')refresh();},60000);
  document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible'){renderLive();refresh();}});
  init();
})();
