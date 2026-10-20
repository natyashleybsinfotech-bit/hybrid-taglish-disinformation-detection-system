// Render real React components with the live API's synthetic test result.
// Headless screenshots verify layout, not installed-extension permissions.
import { createRequire } from 'node:module';
import { readFile, writeFile, mkdir, readdir } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { spawn, spawnSync } from 'node:child_process';
import assert from 'node:assert/strict';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const output=path.join(root,'tmp/ui'); await mkdir(output,{recursive:true});
const screenshots=path.join(root,'docs/verification/ui');await mkdir(screenshots,{recursive:true});
const result=JSON.parse(await readFile(path.join(root,'tmp/ui-real-result.json'),'utf8'));
delete result.research_receipt;
const browser=process.env.SURI_TEST_BROWSER || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const reports=[];
async function capture(html, shot, name, width, height) {
  const profile=path.join(output,'cdp-'+name+'-'+Date.now());
  const proc=spawn(browser,['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check',`--user-data-dir=${profile}`,'--remote-debugging-port=0',pathToFileURL(html).href],{windowsHide:true,stdio:'ignore'});
  let socket;
  try {
    let port;
    for(let i=0;i<100;i++){try{port=(await readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0];break;}catch{await new Promise(resolve=>setTimeout(resolve,100));}}
    if(!port)throw new Error('Headless debugging did not start');
    const tabs=await fetch(`http://127.0.0.1:${port}/json/list`).then(r=>r.json());
    socket=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);
    await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
    let id=0;const pending=new Map();
    socket.onmessage=event=>{const data=JSON.parse(event.data);if(pending.has(data.id)){const [resolve,reject]=pending.get(data.id);pending.delete(data.id);data.error?reject(new Error(JSON.stringify(data.error))):resolve(data.result);}};
    const send=(method,params={})=>new Promise((resolve,reject)=>{const seq=++id;pending.set(seq,[resolve,reject]);socket.send(JSON.stringify({id:seq,method,params}));});
    await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false});
    await send('Runtime.evaluate',{expression:'document.fonts.ready',awaitPromise:true});
    const measured=await send('Runtime.evaluate',{expression:'JSON.stringify({width:innerWidth,clientWidth:document.documentElement.clientWidth,scrollWidth:document.documentElement.scrollWidth})',returnByValue:true});
    const layout=JSON.parse(measured.result.value);assert.equal(layout.width,width);assert.ok(layout.scrollWidth<=layout.clientWidth,`${name} horizontal overflow`);
    const png=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
    await writeFile(shot,Buffer.from(png.data,'base64'));
    return layout;
  } finally {
    socket?.close();
    if(process.platform==='win32')spawnSync('taskkill',['/PID',String(proc.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});else proc.kill();
  }
}
for(const [name, project, component, width, height] of [
  ['popup-empty','chrome-extension','<Popup />',390,900],
  ['popup-result','chrome-extension','<main className="popup-shell"><Result result={result}/></main>',390,1450],
  ['popup-narrow','chrome-extension','<Popup />',320,900],
  ['admin-login','admin-dashboard','<Login onLogin={()=>{}} />',1280,900],
  ['admin-login-narrow','admin-dashboard','<Login onLogin={()=>{}} />',390,900],
  ['admin-research','admin-dashboard','<MemoryRouter initialEntries={["/research"]}><Layout user={{role:"admin"}} onLogout={()=>{}}><Research /></Layout></MemoryRouter>',1280,1000],
  ['admin-research-narrow','admin-dashboard','<MemoryRouter initialEntries={["/research"]}><Layout user={{role:"admin"}} onLogout={()=>{}}><Research /></Layout></MemoryRouter>',390,1450],
]) {
  const base=path.join(root,project), require=createRequire(path.join(base,'package.json'));
  const esbuild=createRequire(path.join(root,'chrome-extension/package.json'))('esbuild');
  const source=`import React from 'react';import {renderToStaticMarkup} from 'react-dom/server';${project==='chrome-extension' ? "import Popup,{Result} from './src/Popup.jsx';" : "import Login from './src/pages/Login.jsx';import Research from './src/pages/Research.jsx';import {Layout} from './src/App.jsx';import {MemoryRouter} from 'react-router-dom';"} const result=${JSON.stringify(result)};export default renderToStaticMarkup(${component});`;
  const built=await esbuild.build({stdin:{contents:source,resolveDir:base,loader:'jsx'},jsx:'automatic',bundle:true,platform:'node',format:'esm',write:false,define:{'import.meta.env':'{}'},banner:{js:"import {createRequire} from 'node:module';const require=createRequire(import.meta.url);"}});
  const modulePath=path.join(output,name+'.mjs');await writeFile(modulePath,built.outputFiles[0].text);
  const {default:markup}=await import(pathToFileURL(modulePath));
  if(name==='popup-result') for(const item of result.linguistic_indicators) {assert.ok(markup.includes(`data-value="${item.value}"`));assert.ok(markup.includes(item.display_name));}
  const assets=path.join(base,'dist/assets'), cssFile=(await readdir(assets)).find(file=>file.endsWith('.css'));
  const css=await readFile(path.join(assets,cssFile),'utf8');
  const html=path.join(output,name+'.html');
  const expanded=name==='popup-result' ? markup.replaceAll('<details ', '<details open ') : markup;
  await writeFile(html,`<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>SuriPH local rendering check</title><style>${css}${name==='popup-result'?'.popup-shell{max-height:none}':''}</style><body>${expanded}</body></html>`);
  const shot=path.join(screenshots,name+'.png');
  const layout=await capture(html,shot,name,width,height);
  const png=await readFile(shot);assert.ok(png.length>10000);
  reports.push({view:name,width,height,layout,screenshot:`verification/ui/${name}.png`,rendered:true});
}
await writeFile(path.join(root,'docs/UI-VERIFICATION.json'),JSON.stringify({actual_component_rendering:true,actual_api_feature_values_matched:true,installed_extension_e2e:false,browser:'headless Chrome',views:reports},null,2));
console.log(JSON.stringify(reports));
