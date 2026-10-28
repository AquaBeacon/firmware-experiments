"""Exercise the production gain workflow offline, including uncalibrated restart."""
from pathlib import Path
import json, subprocess
r=Path(__file__).resolve().parents[1]
source=next(line for line in (r/'web/index.html').read_text(encoding='utf-8').splitlines() if line.startswith('async function gain(){'))
test=r'''
const vm=require('node:vm'),assert=require('node:assert/strict');
const calls=[];let now=0,fail=false;
const ctx={abortGain:false,performance:{now:()=>now+=61000},el:()=>({textContent:''}),
 rangeStop:async()=>calls.push('stop'),post:async p=>calls.push(p),
 cmd:async(t,op,arg)=>{calls.push([t,op,arg]);if(fail&&op===10)throw Error('busy');return {};}};
vm.createContext(ctx);vm.runInContext(SOURCE,ctx);
(async()=>{
 await vm.runInContext('gain()',ctx);
 assert(calls.includes('/api/range/test'));
 assert.deepEqual(calls.filter(Array.isArray).at(-1),['c',3,0x43414c21]);
 assert(calls.filter(Array.isArray).some(c=>c[1]===11));
 calls.length=0;fail=true;await assert.rejects(vm.runInContext('gain()',ctx),/busy/);
 assert(!calls.includes('/api/range/test'));assert.equal(calls.filter(c=>c==='stop').length,2);
 assert.deepEqual(calls.filter(Array.isArray).at(-1),['c',3,0x43414c21]);
 console.log('PASS gain UI: uncalibrated test/restart, failed receiver start and cleanup');
})().catch(e=>{console.error(e);process.exitCode=1});
'''
subprocess.run(['node'],input=test.replace('SOURCE',json.dumps(source)),text=True,encoding='utf-8',check=True)
