// Isolated headless Edge profile. No existing user browser/profile is touched.
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict');
const {chromium}=require('C:/Users/kaanb/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root='C:/Users/kaanb/cloud-studio-repo';
const out='C:/Users/kaanb/CloudCrushing/followup_20260907/evidence';
const server=http.createServer((req,res)=>{
  const filename=path.resolve(root,'.'+decodeURIComponent(new URL(req.url,'http://localhost').pathname));
  if(!filename.startsWith(path.resolve(root)+path.sep)){res.writeHead(403);res.end();return;}
  const type={'.html':'text/html','.js':'text/javascript','.json':'application/json','.png':'image/png'}[path.extname(filename)];
  fs.readFile(filename,(e,data)=>{if(e){res.writeHead(404);res.end();return;}res.setHeader('Content-Type',type||'application/octet-stream');res.end(data);});
});
(async()=>{
  await new Promise(r=>server.listen(0,'127.0.0.1',r));let browser;
  try{
    browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true,
      args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
    const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    const base=`http://127.0.0.1:${server.address().port}`;
    await page.goto(base+'/viewer.html?run=apkcool_L4_chi10');
    await page.waitForFunction(()=>document.getElementById('titleA').textContent.includes('cooling NOT enabled'),null,{timeout:45000});
    await page.waitForFunction(()=>document.getElementById('tlab').textContent.includes('t ='),null,{timeout:30000});
    const initial=await page.locator('#titleA').innerText();
    assert.match(initial,/cooling NOT enabled/);
    assert(await page.locator('#runs .grp').filter({hasText:'AthenaPK (GPU) M=0.5'}).count()>0);
    assert(await page.locator('#runs .grp').filter({hasText:'Athena++ M=1.5'}).count()>0);
    const before=await page.locator('#tlab').innerText();
    const lastURL=await page.evaluate(()=>{const d=window.__A.dense;return d.base+d.tag+'/'+d.index.frames.at(-1);});
    await page.route(lastURL,async route=>{await new Promise(r=>setTimeout(r,750));await route.continue();});
    await page.locator('#slider').fill(await page.locator('#slider').getAttribute('max'));
    await page.locator('#slider').dispatchEvent('input');
    assert.match(await page.locator('#tlab').innerText(),/loading/);
    assert((await page.locator('#tlab').innerText()).startsWith(before.replace(/ \(loading…\)$/,'')));
    await page.waitForFunction(()=>window.__A.cur===window.__A.times.length-1 && !!window.__A.dense.shown,null,{timeout:30000});
    await page.waitForFunction(()=>!document.getElementById('tlab').textContent.includes('loading'),null,{timeout:30000});
    await page.screenshot({path:path.join(out,'viewer_cooling_warning.png')});
    await page.locator('#sideHide').click();assert(await page.locator('#sideShow').isVisible());
    await page.locator('#sideShow').click();assert(await page.locator('#side').isVisible());
    assert.deepEqual(errors,[]);
    fs.writeFileSync(path.join(out,'browser_smoke.json'),JSON.stringify({passed:true,scope:'local production-bundle browser smoke using real streamed historical frame',initial_title:initial,time_label:await page.locator('#tlab').innerText(),errors},null,2));
    console.log('PASS: real streamed frame, warning and distinct Mach labels, slider and collapsible panel; no JavaScript errors.');
  }finally{if(browser)await browser.close();server.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
