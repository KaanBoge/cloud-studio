'use strict';
const $=id=>document.getElementById(id), canvas=$('scene'),ctx=canvas.getContext('2d');
let catalog,runs=[],current,comparison=null,frame=10,playing=false,timer=null,recording=false,drawGeneration=0;
const images=new Map();
function image(run,view){const key=run.id+'-'+view;if(!images.has(key))images.set(key,new Promise((resolve,reject)=>{const im=new Image();im.onload=()=>resolve(im);im.onerror=()=>{images.delete(key);reject(new Error('Could not load '+run.label+' image. Please retry.'));};im.src='assets/recent/'+key+'.png';}));return images.get(key);}
function text(s,x,y,size=24,color='#d5dbe7',align='left'){ctx.font=`${size}px system-ui, sans-serif`;ctx.fillStyle=color;ctx.textAlign=align;ctx.fillText(s,x,y);}
function panel(run,im,x,y,w,h){const view=$('view').value,labels=$('labels').checked,sw=view==='edge'?256:128;
 const pad=labels?85:15,aw=w-pad-20,ah=h-160,scale=Math.min(aw/sw,ah/128),iw=sw*scale,ih=128*scale,ix=x+pad+(aw-iw)/2,iy=y+85+(ah-ih)/2;
 if(labels){text(run.label,x+pad,y+30,comparison?23:30,'#f1f4fb');text(`${view==='edge'?'Edge-on':'Face-on'}  ·  t/tcc = ${run.frames[frame].time.toFixed(3)}`,x+pad,y+65,22,'#a5b1c5');}
 ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality='high';ctx.drawImage(im,0,frame*128,sw,128,ix,iy,iw,ih);
 if(labels){const ticks=view==='edge'?[-3,2,7,12,17]:[-5,0,5],lo=ticks[0],hi=ticks[ticks.length-1];
  ctx.strokeStyle='#6c7586';ctx.lineWidth=1;ctx.strokeRect(ix,iy,iw,ih);
  for(const v of ticks)text(String(v),ix+(v-lo)/(hi-lo)*iw,iy+ih+31,20,'#acb7c9','center');
  for(const v of [-5,0,5])text(String(v),ix-16,iy+ih-(v+5)/10*ih+6,20,'#acb7c9','right');
  text(view==='edge'?'Distance along wind / R':'Transverse distance / R',ix+iw/2,iy+ih+66,21,'#acb7c9','center');
  ctx.save();ctx.translate(ix-57,iy+ih/2);ctx.rotate(-Math.PI/2);text('Transverse distance / R',0,0,21,'#acb7c9','center');ctx.restore();
 }
}
function colorbar(){const x=630,y=968,w=660,h=18;catalog.colormap.forEach((c,i)=>{ctx.fillStyle=`rgb(${c.map(x=>Math.round(x*255)).join(',')})`;ctx.fillRect(x+i*w/256,y,w/256+1,h);});
 for(const v of [.008,.05,.2,1,5])text(String(v),x+(Math.log(v/.008)/Math.log(5/.008))*w,y+45,19,'#a5b1c5','center');
 text('Column density  Σ / (ρc,0 R)  ·  logarithmic scale',960,y-17,22,'#c6cfdd','center');}
async function draw(){const gen=++drawGeneration;try{const view=$('view').value,ims=await Promise.all([image(current,view),comparison?image(comparison,view):null]);if(gen!==drawGeneration)return;
 ctx.fillStyle='#070911';ctx.fillRect(0,0,1920,1080);
 if(comparison){panel(current,ims[0],22,80,926,820);panel(comparison,ims[1],972,80,926,820);}else panel(current,ims[0],65,66,1790,820);
 if($('labels').checked){colorbar();text('Cloud Crushing Studio · Kaan Boge',42,1048,18,'#7e8da5');text('Saved states · no interpolated fluid motion',1878,1048,18,'#7e8da5','right');}
 $('timeLabel').textContent=current.frames[frame].time.toFixed(2)+' tcc';$('error').hidden=true;
 }catch(e){stop();$('error').hidden=false;$('error').textContent=e.message;throw e;}}
function stop(){playing=false;clearTimeout(timer);$('play').textContent='▶ Play';}
async function tick(){if(!playing)return;frame=(frame+1)%current.frames.length;$('time').value=frame;try{await draw();if(playing)timer=setTimeout(tick,Number($('speed').value));}catch{}}
function select(){stop();current=runs.find(r=>r.id===$('run').value);comparison=runs.find(r=>r.id===$('compare').value)||null;$('title').textContent=current.label;$('rotate3d').href='viewer.html?run=new_'+current.id;$('meta').textContent=`Mach ${current.mach} · n = ${current.n} · ${current.cells.toLocaleString()} cells / elements · 11 saved views through 5 tcc`;$('note').textContent=current.note+(comparison?' Comparison — '+comparison.label+': '+comparison.note:'');document.querySelectorAll('.card').forEach(e=>e.classList.toggle('selected',e.dataset.id===current.id));const u=new URL(location);u.searchParams.set('run',current.id);history.replaceState(null,'',u);draw().catch(()=>{});}
function download(blob,name){const u=URL.createObjectURL(blob),a=document.createElement('a');a.href=u;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),60000);}
function filename(){return current.id+(comparison?'_vs_'+comparison.id:'')+'-'+$('view').value;}
async function record(){if(recording)return;stop();const type=['video/webm;codecs=vp9','video/webm;codecs=vp8','video/mp4'].find(t=>window.MediaRecorder&&MediaRecorder.isTypeSupported(t));if(!canvas.captureStream||!type){$('message').textContent='Video capture is unavailable in this browser. Use the system screen recorder.';return;}
 recording=true;const disabled=[...document.querySelectorAll('select,button,input')];disabled.forEach(e=>e.disabled=true);let stream,rec;const chunks=[];
 try{frame=0;$('time').value=frame;await draw();stream=canvas.captureStream(10);rec=new MediaRecorder(stream,{mimeType:type,videoBitsPerSecond:8000000});rec.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};const done=new Promise((resolve,reject)=>{rec.onstop=resolve;rec.onerror=e=>reject(e.error||new Error('Recording failed'));});rec.start();
 for(let i=0;i<current.frames.length;i++){frame=i;$('time').value=i;await draw();$('message').textContent=`Recording saved frame ${i+1} / ${current.frames.length}…`;await new Promise(r=>setTimeout(r,Math.max(250,Number($('speed').value))));}
 rec.stop();await done;const blob=new Blob(chunks,{type});if(!blob.size)throw new Error('Empty video');download(blob,filename()+'.'+(type.startsWith('video/mp4')?'mp4':'webm'));$('message').textContent='Video saved — one complete cycle.';
 }catch(e){if(rec&&rec.state!=='inactive')rec.stop();$('message').textContent='Capture failed: '+e.message;}finally{if(stream)stream.getTracks().forEach(t=>t.stop());disabled.forEach(e=>e.disabled=false);recording=false;}}
function cards(){const filter=$('filter').value;$('cards').replaceChildren();for(const run of runs){if(filter==='cooling'?run.cooling!=='tabular':filter!=='all'&&run.chi!==Number(filter))continue;const b=document.createElement('button');b.className='card'+(run===current?' selected':'');b.dataset.id=run.id;b.setAttribute('aria-label','View '+run.label);const c=document.createElement('canvas');c.width=512;c.height=256;const info=document.createElement('div'),strong=document.createElement('strong'),small=document.createElement('small');strong.textContent=run.label;small.textContent='5 tcc · edge-on + face-on · images & video';info.append(strong,small);b.append(c,info);b.onclick=()=>{$('run').value=run.id;select();$('screen').scrollIntoView({behavior:'smooth',block:'center'});};$('cards').append(b);image(run,'edge').then(im=>{const g=c.getContext('2d');g.imageSmoothingEnabled=true;g.imageSmoothingQuality='high';g.drawImage(im,0,1280,256,128,0,0,512,256);}).catch(()=>{small.textContent='Preview unavailable — select to retry';});}}
async function init(){try{const r=await fetch('assets/recent/catalog.json');if(!r.ok)throw new Error('Catalog HTTP '+r.status);catalog=await r.json();runs=catalog.runs;for(const r of runs){$('run').add(new Option(r.label,r.id));$('compare').add(new Option(r.label,r.id));}const requested=new URL(location).searchParams.get('run');$('run').value=runs.some(r=>r.id===requested)?requested:'enzo-1000';$('count').textContent=runs.length+' completed runs';select();cards();
 $('run').onchange=select;$('compare').onchange=select;$('view').onchange=()=>draw().catch(()=>{});$('labels').onchange=()=>draw().catch(()=>{});$('time').oninput=()=>{stop();frame=Number($('time').value);draw().catch(()=>{});};$('play').onclick=()=>{if(playing)stop();else{playing=true;$('play').textContent='Ⅱ Pause';tick();}};$('filter').onchange=cards;$('full').onclick=()=>{const p=document.fullscreenElement?document.exitFullscreen():$('screen').requestFullscreen();p.catch(e=>{$('message').textContent=e.message;});};$('picture').onclick=async()=>{stop();await draw();canvas.toBlob(blob=>{if(blob){download(blob,filename()+'-t'+current.frames[frame].time.toFixed(2)+'.png');$('message').textContent='1920 × 1080 PNG saved.';}},'image/png');};$('record').onclick=record;
 document.addEventListener('visibilitychange',()=>{if(document.hidden&&!recording)stop();});
 }catch(e){$('error').hidden=false;$('error').textContent='Unable to open the gallery: '+e.message;$('count').textContent='Load failed';}}
init();
