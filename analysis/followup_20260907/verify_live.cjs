// Read-only verification of the deployed content, not merely the Git commit.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const root='C:/Users/kaanb/cloud-studio-repo';
const sha=s=>crypto.createHash('sha256').update(s.replace(/\r\n/g,'\n')).digest('hex');
(async()=>{
  const files=['viewer.html','verification.html','analysis/followup_20260907/evidence/regression_suite.json',
    'analysis/followup_20260907/evidence/tracking_fulltime.json','analysis/followup_20260907/evidence/cooling_audit.json',
    'analysis/followup_20260907/evidence/tracking_extended.json'];
  const result=[];
  for(const name of files){
    const r=await fetch('https://kaanboge.github.io/cloud-studio/'+name+'?verify='+Date.now(),{cache:'no-store'});
    const body=await r.text();const wanted=sha(fs.readFileSync(path.join(root,name),'utf8'));
    result.push({file:name,http_status:r.status,expected_sha256:wanted,live_sha256:sha(body),matches:r.ok&&wanted===sha(body)});
  }
  const passed=result.every(r=>r.matches);console.log(JSON.stringify({passed,files:result},null,2));
  if(passed)fs.writeFileSync('C:/Users/kaanb/CloudCrushing/followup_20260907/evidence/live_deployment.json',JSON.stringify({passed,files:result},null,2));
  process.exitCode=passed?0:75;
})().catch(e=>{console.error(e);process.exitCode=1;});
