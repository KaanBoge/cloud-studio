const fs=require('node:fs'),assert=require('node:assert/strict'),path=require('node:path');
process.chdir(path.resolve(__dirname,'..'));
const c=JSON.parse(fs.readFileSync('data/studio-catalog.json'));
assert.equal(new Set(c.entries.map(r=>r.id)).size,c.entries.length,'Duplicate entry ID');
const movies=new Set();let links=0;
for(const r of c.entries){
 for(const f of [r.poster,...(r.images||[]),...(r.variants||[]).flatMap(v=>[v.src,v.poster])].filter(Boolean)){
  assert(!path.isAbsolute(f)&&!f.includes('..'),'Unsafe asset path');assert(fs.existsSync(f)&&fs.statSync(f).size>0,'Missing '+f);links++;
 }
 for(const v of r.variants||[])movies.add(v.src);
 if(r.viewer)assert(r.viewer.startsWith('viewer.html?run='));
 if(r.kind==='recent'){assert.equal(r.frames,11);assert(r.end>=4.99&&r.end<=5.01);assert.equal(r.variants.length,2);assert.equal(r.level,5);}
}
assert.equal(movies.size,c.counts.films);
for(const name of fs.readdirSync('assets/movies').filter(n=>n.endsWith('.mp4')))assert(movies.has('assets/movies/'+name),'Unlisted film '+name);
const recent=c.entries.filter(r=>r.kind==='recent');assert.equal(recent.length,17);
assert.equal(recent.find(r=>r.id==='new_apk-hlle-on').physics,'tabular');
assert.equal(recent.find(r=>r.id==='new_apk-hllc-plm-off').physics,'none');
const p=JSON.parse(fs.readFileSync('assets/recent3d/new_apk-hllc-plm-off/index.json'));
assert.equal(p.frames.length,21);assert.equal(p.times.length,21);assert(p.times.every((t,i)=>i===0||t>p.times[i-1]));
for(const f of p.frames)assert(fs.existsSync('assets/recent3d/new_apk-hllc-plm-off/'+f));
console.log(JSON.stringify({passed:true,entries:c.entries.length,recent:recent.length,uniqueFilms:movies.size,localAssetReferences:links,newMeshes:p.frames.length}));
