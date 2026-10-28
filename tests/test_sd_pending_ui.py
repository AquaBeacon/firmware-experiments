"""Run the actual console command helper: accepted SD start is not completion."""
from pathlib import Path
import json,re,subprocess
r=Path(__file__).resolve().parents[1]
source=re.search(r'^const cmd=async.*$',(r/'web/index.html').read_text(encoding='utf-8'),re.M).group()
test=r'''
const vm=require('node:vm'),assert=require('node:assert/strict');let responses=[],calls=[],now=0;
const ctx={el:()=>({textContent:''}),performance:{now:()=>now+=1000},pause:async()=>{},text:r=>r.state,calibrationPreflight:async()=>0,
 post:async path=>{calls.push(path);return responses.shift()}};vm.createContext(ctx);vm.runInContext(SOURCE,ctx);
(async()=>{
 responses=[{arg:1},{state:'INITIALIZING'},{state:'NONE'}];await vm.runInContext("cmd('c',3)",ctx);
 assert.deepEqual(calls,['/api/control/c/3/0','/api/control/c/1/0','/api/control/c/1/0']);
 calls=[];responses=[{arg:1},{state:'INIT_TIMEOUT'}];await assert.rejects(vm.runInContext("cmd('p',4)",ctx),/制限時間内/);
 calls=[];responses=[{arg:0}];await vm.runInContext("cmd('p',3)",ctx);assert.equal(calls.length,1);
 responses=Array.from({length:100},()=>({state:'INITIALIZING'}));responses.unshift({arg:1});
 await assert.rejects(vm.runInContext("cmd('p',3)",ctx),/準備が完了しません/);
 console.log('PASS actual SD start UI: pending INFO polling, completed storage, error, ready path and bounded wait');
})().catch(e=>{console.error(e);process.exitCode=1});
'''
subprocess.run(['node'],input=test.replace('SOURCE',json.dumps(source)),text=True,encoding='utf-8',check=True)
