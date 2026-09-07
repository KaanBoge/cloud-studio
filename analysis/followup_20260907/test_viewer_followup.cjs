const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync('C:/Users/kaanb/CloudCrushing/studio/viewer.html','utf8');
const source=html.match(/<script type="module">([\s\S]*?)<\/script>/)[1];
new vm.SourceTextModule(source);
const context=vm.createContext({});
const metadata=source.slice(source.indexOf('const CODE_OF ='),source.indexOf('// only integer-ladder'));
vm.runInContext(metadata,context);
const m=context.meta;
assert.equal(m('apkM05_L4_chi100').code,'AthenaPK (GPU) M=0.5');
assert.equal(m('athppM15_L4_chi10').code,'Athena++ M=1.5');
assert.equal(m('enzoM5_L4_chi10').code,'Enzo M=5');
assert.equal(m('athwM05_L4_chi10').code,'Athena 4.2 M=0.5');
assert.match(m('apkcool_L6_chi100').code,/NOT enabled/);
assert.match(m('athppgal_L4_chi100').code,/unvalidated/);
assert.equal(m('apk3d_chi10_512').lvl,6);
assert.equal(m('apk_L5_chi1000').chi,1000);
vm.runInContext(source.match(/function normalizeFrameIndex\(index\) \{[\s\S]*?\n\}/)[0],context);
const index={times:[5,0,6,5],frames:['end','initial','later','duplicate']};
context.normalizeFrameIndex(index);
assert.deepEqual(Array.from(index.times),[0,5,6]);
assert.deepEqual(Array.from(index.frames),['initial','end','later']);
for(const bad of [null,NaN,Infinity,'1',-1]){
  assert.throws(()=>context.normalizeFrameIndex({times:[bad],frames:['a']}));
}
assert.throws(()=>context.normalizeFrameIndex({times:[],frames:['a']}));
assert.throws(()=>context.normalizeFrameIndex({times:[],frames:[]}));
assert.match(html,/function updateDisplayedTimes/);
assert.match(html,/p\.times\[p\.cur\]/);
console.log('PASS: full module parses, Mach variants distinct, cooling/tracking labels honest, all unique measured times including t>5 preserved, malformed times rejected.');
