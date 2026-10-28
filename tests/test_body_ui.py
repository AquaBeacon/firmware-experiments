"""Exercise production body workflow and warning before any experiment mutation."""
from pathlib import Path
import re,json,subprocess
r=Path(__file__).resolve().parents[1];html=(r/'web/index.html').read_text(encoding='utf-8')
block=html.split('// BODY_CALIBRATION_BEGIN')[1].split('// BODY_CALIBRATION_END')[0]
command=re.search(r'^const cmd=async.*$',html,re.M).group()
test=r'''
const vm=require('node:vm'),assert=require('node:assert/strict');
const elements={},timers=[],calls=[];let ready=false,cameraReady=false,issueMask=0,failStart=false,failCheck=false;
const el=id=>elements[id]??=({value:id==='bodyTarget'?'p':'1',files:[],querySelector(){return {}},replaceChildren(...v){this.children=v},showModal(){this.open=true},close(){this.open=false}});
const ctx={console,el,ArrayBuffer,DataView,Uint8Array,Date,JSON,Number,Math,TextDecoder,busy:false,bodyLastPoll:0,overviewChildConnected:true,selectedTab:'sensors',
 document:{createElement:()=>({append(){}}),getElementById:()=>null},clearTimeout:()=>{},setTimeout:f=>{timers.push(f);return timers.length},
 text:r=>JSON.stringify(r.data),post:async path=>{calls.push(path);if(path.includes('/22/')){if(failCheck)throw Error('unsupported');return {data:{x:issueMask,l:0,e:31,z:0,y:ready?1:0}};}if(failStart&&path.includes('/17/')){const e=Error('入力が不正です');e.control={hex:'01',arg:issueMask,data:{a:0,m:0,p:0,g:0,r:0}};throw e;}return {data:{a:0,m:31,p:0,c:1,g:0,v:0,t:0,r:ready?1:0,b:1,k:cameraReady?1:0,o:31,q:0,s:0,d:0}}},
 rangeStop:async()=>calls.push('rangeStop'),selectTab:k=>{calls.push('tab:'+k)},stopBoth:async()=>calls.push('stop'),both:async(op,arg)=>calls.push(['both',op,arg]),setBusy:v=>{ctx.busy=v}};
vm.createContext(ctx);vm.runInContext(COMMAND,ctx);vm.runInContext(SOURCE,ctx);
const tick=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
 vm.runInContext('renderParentPreparation(null)',ctx);assert.match(el('parentPreparation').textContent,/状態不明/);
 ctx.prep={local:{flags:2},spresense:{link_fresh:true,sd_ok:true,imu_ok:true,calibration_applied:true,calibration_generation:1,recording:true,pps_paired:true,imu_time_ready:true},mag_calibration:{present:true,fresh:true,enabled:true,loaded:true},parent_calibration:{calibrations_match:true},utc:{valid:true,source:'gps_pps_candidate'}};
 vm.runInContext('renderParentPreparation(prep)',ctx);assert.match(el('parentPreparation').textContent,/準備条件を確認/);ctx.prep.parent_calibration.calibrations_match=false;vm.runInContext('renderParentPreparation(prep)',ctx);assert.match(el('parentPreparation').textContent,/手順5/);
 await vm.runInContext('prepareParentCapture()',ctx);assert(calls.includes('/api/control/p/19/0'));assert(!calls.includes('rangeStop'));assert(!calls.some(p=>typeof p==='string'&&p.includes('/api/control/c/')));calls.length=0;
 let p=vm.runInContext('startExperiment(true)',ctx);await tick();assert(el('calibrationWarning').open);assert(!calls.includes('stop'));el('calibrationWarningBack').onclick();await assert.rejects(p);assert(!calls.includes('stop'));
 calls.length=0;p=vm.runInContext('startExperiment(true)',ctx);await tick();el('calibrationWarningContinue').onclick();await p;assert(calls.includes('stop'));assert.deepEqual(calls.filter(Array.isArray).at(-1),['both',3,0x43414c21]);
 calls.length=0;ready=true;await vm.runInContext('startExperiment(false)',ctx);assert(!el('calibrationWarning').open);assert.deepEqual(calls.filter(Array.isArray).at(-1),['both',3,0]);
 vm.runInContext("renderBody({a:1,m:3,p:2,c:1,g:0,v:0,t:0,r:0,b:1},'p',{x:1,e:5,z:1,y:0})",ctx);assert(el('bodyStart').disabled);assert(!el('bodyPhaseEnd').disabled);assert(el('bodyFinish').disabled);assert.match(el('bodyState').textContent,/解析前/);
 timers.at(-1)();assert.match(el('bodyState').textContent,/状態不明/);assert(el('bodyStart').disabled);
 el('bodyTarget').value='c';ctx.overviewChildConnected=false;await el('bodyTarget').onchange();await tick();assert(el('bodyStart').disabled);el('bodyTarget').value='p';
 calls.length=0;el('bodySolution').files=[{size:100,text:async()=>JSON.stringify({format:'AquaBeaconBodySolution1',capture:1,boot:1,imu:1,mag:1,axes:3,camera:0,imu_q:[2,0,0,0],mag_q:[1,0,0,0],camera_scale:1,camera_offset_us:0})}];await el('bodyImport').onclick();assert.equal(calls.length,0);assert.match(el('bodyMessage').textContent,/軸変換が不正/);
 calls.length=0;el('bodySolution').files=[{size:100,text:async()=>JSON.stringify({format:'AquaBeaconBodySolution1',capture:1,boot:1,imu:1,mag:1,axes:3,camera:1,imu_q:[1,0,0,0],mag_q:[1,0,0,0],camera_scale:1,camera_offset_us:1792886400000000})}];await el('bodyImport').onclick();assert(calls.some(p=>p.includes('/api/control/p/21/')));
 calls.length=0;ready=false;cameraReady=false;await vm.runInContext('startRangeChecked()',ctx);assert.deepEqual(calls,['/api/range/start']);
 vm.runInContext("renderBody({a:1,m:0,p:5,c:2,g:1,v:3,r:0,o:16,s:12,d:1,q:1},'p',{x:1,e:12,z:1,y:1})",ctx);assert.match(el('bodyMotionGuide').textContent,/②/);assert(el('bodyPhaseEnd').disabled);vm.runInContext("renderBody({a:1,m:0,p:5,c:2,g:1,v:3,r:0,o:16,s:31,d:3,q:2},'p',{x:1,e:31,z:1,y:1})",ctx);assert(!el('bodyPhaseEnd').disabled);vm.runInContext("renderBody({a:1,m:16,p:0,c:2,g:1,v:3,r:0,o:16,s:31,d:3,q:2},'p',{x:1,e:31,z:1,y:1})",ctx);assert(!el('bodyFinish').disabled);
 // A missing Spresense link makes dependent conditions unknown, not evidence of missing calibration.
 vm.runInContext("renderBody({a:0,m:0,p:0,g:0,r:0},'p',{x:32384,l:0,e:0,z:0,y:0})",ctx);
 assert.equal(el('bodyRequirements').children.length,1);assert.match(el('bodyRequirements').children[0].textContent,/通信復帰後に再判定/);assert(el('bodyStart').disabled);
 // Initial axes missing is allowed when every actual start prerequisite is ready.
 vm.runInContext("renderBody({a:0,m:0,p:0,c:0,g:0,v:0,r:0,o:31},'p',{x:0,l:0,e:0,z:0,y:0})",ctx);
 assert(!el('bodyStart').disabled);assert.match(el('bodyAxes').textContent,/初回/);assert.match(el('bodyState').textContent,/収録していません/);assert(el('bodyPhaseBegin').disabled);
 // Multiple concrete start failures remain visible after status refresh and expiry.
 issueMask=4|2048|32768;failStart=true;await vm.runInContext('bodyCommand(17)',ctx);
 assert.match(el('bodyMessage').textContent,/通常ログが停止/);assert.match(el('bodyMessage').textContent,/Spresenseの通常記録/);assert.match(el('bodyMessage').textContent,/親機のGPS/);
 assert.equal(el('bodyRequirements').children.length,3);const error=el('bodyMessage').textContent;
 await vm.runInContext('bodyCommand(19)',ctx);assert.equal(el('bodyMessage').textContent,error);timers.at(-1)();assert.equal(el('bodyMessage').textContent,error);assert.match(el('bodyState').textContent,/状態不明/);assert(el('bodyStart').disabled);
 // Restore condition display, incomplete diagnostic firmware, cancelled capture.
 failStart=false;failCheck=true;await vm.runInContext('bodyCommand(19)',ctx);assert(el('bodyStart').disabled);assert.match(el('bodyRequirementsSummary').textContent,/旧ファーム/);failCheck=false;
 vm.runInContext("renderBody({a:0,m:1,p:0,g:0,r:0,o:31},'p',{x:4,e:0,z:3,y:0})",ctx);assert.match(el('bodyState').textContent,/中止/);
 vm.runInContext("renderBody({a:1,m:0,p:1,g:0,r:0,o:31},'p',{x:1,e:3,z:1,y:0})",ctx);assert(el('bodyPhaseEnd').disabled);assert.match(el('bodyPhaseReason').textContent,/あと2秒/);
 vm.runInContext("renderBody({a:1,m:0,p:1,g:0,r:0,o:31},'p',{x:1,e:5,z:1,y:0})",ctx);assert(!el('bodyPhaseEnd').disabled);
 // Preparation never sends start to a body capture already running.
 console.log('PASS body UI: warnings, concrete multi-cause errors, error retention, initial axes, legacy unknown, time gates, expiry and movement');

})().catch(e=>{console.error(e);process.exitCode=1});
'''
subprocess.run(['node'],input=test.replace('COMMAND',json.dumps(command)).replace('SOURCE',json.dumps(block)),text=True,encoding='utf-8',check=True)
