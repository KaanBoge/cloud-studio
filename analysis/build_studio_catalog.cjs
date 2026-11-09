// Consolidate display catalogs without reading or changing native simulation data.
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.resolve(__dirname,'..');process.chdir(root);
const read=p=>fs.readFileSync(p,'utf8');
const ctx={};ctx.window=ctx;vm.createContext(ctx);
for(const f of ['data/manifest.js','data/densemap.js','assets/recent3d/catalog.js'])vm.runInContext(read(f),ctx);
const source=read('viewer.html');
vm.runInContext('const recent3D=RECENT_3D;'+source.slice(source.indexOf('let ids ='),source.indexOf('// ------------------------------------------------------------------- panes'))+';this.viewerEntries=ids.map(id=>({id,...meta(id)}));',ctx);
const recent=JSON.parse(read('assets/recent/catalog.json')).runs;
const inv=new Map(JSON.parse(read('data/streaming-inventory.json')).runs.map(x=>[x.run_id,x]));
const family=s=>s.replace(/^New · /,'').split(' χ')[0].replace(/ \(GPU\)/,'').replace(/ 4\.[28]/,'').split(' M=')[0].split(' · ')[0].split(' MHD')[0].replace(/^ramses$/,'RAMSES');
const names={apk:'AthenaPK',apk3d:'AthenaPK',athena:'Athena',athpp:'Athena++',athpp3d:'Athena++',athw:'Athena',athw3d:'Athena',flash:'FLASH',f3d:'FLASH',f:'FLASH',flashx:'Flash-X',enzo:'Enzo',enzoe:'Enzo-E',arepo:'Arepo',gzmfm:'GIZMO MFM',gzmfv:'GIZMO MFV',gizmo:'GIZMO',ramses:'RAMSES',g4:'Gadget-4',gas:'Gasoline'};
const movies=new Map();
const movieFiles=[...new Map(ctx.STUDIO_MOVIES.map(m=>[m.src,m])).values()];
for(const f of fs.readdirSync('assets/movies').filter(f=>f.endsWith('.mp4'))){
 if(!movieFiles.some(m=>m.src==='assets/movies/'+f))movieFiles.push({src:'assets/movies/'+f,name:f.slice(0,-4)});
}
for(const m of movieFiles){
 if(!fs.existsSync(m.src))throw Error('Missing movie '+m.src);
 const base=m.name.replace(/_(slow|smooth)$/,'');
 if(!movies.has(base))movies.set(base,[]);
 movies.get(base).push({src:m.src,label:m.name==='flash3d_chi100_lref6_smooth'?'Repaired · 30 fps held frames':m.name.endsWith('_smooth')?'Smooth · legacy export':m.name.endsWith('_slow')?'Slow · legacy export':'Original',poster:'assets/posters/'+base+'.jpg'});
}
const entries=[];
for(const r of recent){
 const video=['edge','face'].map(v=>({src:`assets/films/${r.id}-${v}.mp4`,label:v==='edge'?'Edge-on · 1080p':'Face-on · 1080p',poster:`assets/posters/${r.id}-${v}.jpg`}));
 entries.push({id:'new_'+r.id,label:r.label,code:family(r.label),chi:r.chi,level:5,physics:r.cooling,kind:'recent',status:r.status,frames:r.frames.length,end:r.frames.at(-1).time,poster:`assets/posters/${r.id}-edge.jpg`,viewer:'viewer.html?run=new_'+r.id,projection:'recent.html?run='+r.id,variants:video,note:r.note,filmNote:`11 real saved states, held for 2 seconds each. Spatial resampling improves display; no invented intervening fluid motion. ${r.note}`});
}
for(const m of ctx.viewerEntries){
 if(m.id.startsWith('new_'))continue;
 const i=inv.get(m.id),partial=i&&i.last_t_tcc<4.99;
 const physics=m.id.includes('_mhd_')?'mhd':/^(apk|athpp|athw|enzo|flash|arepo|gzm|ramses)/.test(m.id)?'none':'unknown';
 entries.push({id:m.id,label:m.code+' · χ'+m.chi+' · L'+m.lvl,code:family(m.code),chi:m.chi,level:m.lvl,physics,kind:'3d',status:partial?'Partial historical coverage':m.id.startsWith('gas_')?'On hold · historical':'Historical display',frames:i?.index_frame_count,end:i?.last_t_tcc,viewer:'viewer.html?run='+encodeURIComponent(m.id),note:'Historical display; matched physics and convergence are not certified.'+(m.id.startsWith('apkcool')?' Cooling was NOT enabled.':'')});
}
for(const [id,variants] of movies){
 const code=names[id.split('_')[0]]||'Other',chi=Number((id.match(/chi(\d+)|_d(\d+)/)||[]).slice(1).find(Boolean))||null,level=Number((id.match(/_[lL](\d)/)||[])[1])||null;
 entries.push({id:'film_'+id,label:id.replaceAll('_',' '),code,chi,level,physics:'unknown',kind:'film',status:'Legacy film',variants,poster:variants[0].poster,note:variants.length+' preserved video version'+(variants.length===1?'':'s'),filmNote:'Historical rendered film. Slow/smooth variants retain their original rendering and timing; interpolation provenance is not certified. Video seconds are playback time, not solver time.'});
}
for(const g of ctx.STUDIO_GALLERY){
 const preview=g.files.find(f=>/Slice|slice|dens|proj/i.test(f))||g.files[0];
 entries.push({id:'gallery_'+g.dir.split('/').pop(),label:g.tag.replaceAll('_',' '),code:family(g.code==='ramses'?'RAMSES':g.code),chi:g.chi||null,level:null,physics:'unknown',kind:'image',status:'Historical image set',poster:g.dir+'/'+preview,images:g.files.map(f=>g.dir+'/'+f),note:g.kind,projection:'archive.html#gallery'});
}
const out={schema:'cloud-studio-library/1',description:'Display entries, not a count of independently validated simulations. Existing variants and partial runs are preserved.',counts:{runs:ctx.viewerEntries.length,codes:new Set(ctx.viewerEntries.map(m=>family(m.code))).size,films:[...movies.values()].reduce((n,v)=>n+v.length,0)+recent.length*2},entries};
fs.writeFileSync('data/studio-catalog.json',JSON.stringify(out));
console.log(JSON.stringify({entries:entries.length,...out.counts}));
