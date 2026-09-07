const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const html = fs.readFileSync('C:/Users/kaanb/CloudCrushing/studio/viewer.html','utf8');
const source = html.match(/<script type="module">([\s\S]*?)<\/script>/)[1];
new vm.SourceTextModule(source); // Parse the entire module, including browser-only code.
const checker = source.match(/function validDiagnostics\(d\) \{[\s\S]*?\n\}/)[0];
const context = vm.createContext({});
vm.runInContext(checker, context);
const good = {schema_version:2,series:[{t_over_tcc:0,dense_mass_over_initial_dense_mass:1},{t_over_tcc:1,dense_mass_over_initial_dense_mass:.5}]};
assert.equal(context.validDiagnostics(good),true);
assert.equal(context.validDiagnostics({series:[{t:0,mass_frac:.1}]}),false);
for (const value of [NaN,Infinity,-1]) {
  const bad=structuredClone(good);bad.series[1].dense_mass_over_initial_dense_mass=value;
  assert.equal(context.validDiagnostics(bad),false);
}
const duplicate=structuredClone(good);duplicate.series[1].t_over_tcc=0;
assert.equal(context.validDiagnostics(duplicate),false);
assert.match(html,/Historical mass curves withheld/);
assert.match(html,/verification\.html/);
assert.match(html,/function updateDisplayedTimes/);
console.log('Viewer module parses; corrected diagnostic accepted; legacy, duplicate and invalid series rejected; t label retained.');
