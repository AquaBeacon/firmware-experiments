"""Run actual distance display and known-distance controls offline."""
from pathlib import Path
import json, subprocess
r=Path(__file__).resolve().parents[1]
html=(r/'web/index.html').read_text(encoding='utf-8')
source=html.split('// RANGE_CONSOLE_BEGIN')[1].split('// RANGE_CONSOLE_END')[0]
test=r'''
const vm=require('node:vm'),assert=require('node:assert/strict');const elements={},calls=[];
const el=id=>elements[id]??=({checked:false,value:'',replaceChildren(...v){this.children=v}});
const ctx={Number,Math,el,document:{createElement:()=>({})},post:async p=>{calls.push(p);return {range_last:ctx.s.range_last}}};
vm.createContext(ctx);vm.runInContext(SOURCE,ctx);
ctx.s={ranging:false,link_age_ms:20,range_last:{has_result:true,shot:7,state:2,age_ms:900,tof_us:100,raw_m:.15,distance_m:.1,correction_applied:true,profile:2,calibration:{ready:true,count:31,loaded:true}}};
vm.runInContext('renderRange(s)',ctx);assert.match(el('experimentRange').textContent,/0.1000 m.*最後の結果/);assert(!el('rangeCalSave').disabled);
ctx.s.range_last.state=4;vm.runInContext('renderRange(s)',ctx);assert.match(el('experimentRange').textContent,/取得異常/);assert(!el('experimentRange').textContent.includes('0.1000'));
ctx.s.range_last.state=2;ctx.s.range_last.distance_m=null;vm.runInContext('renderRange(s)',ctx);assert.match(el('experimentRange').textContent,/負/);
vm.runInContext('renderRange(null)',ctx);assert.match(el('experimentRange').textContent,/通信途絶/);assert(el('rangeCalStart').disabled);
(async()=>{
 await assert.rejects(vm.runInContext("rangeCalibration('start')",ctx));assert.equal(calls.length,0);
 el('rangeFixed').checked=true;el('rangeKnownCm').value='10';el('rangeSpeed').value='1500';
 await vm.runInContext("rangeCalibration('start')",ctx);assert.equal(calls.at(-1),'/api/range-calibration/start/100/1500000');
 await vm.runInContext("rangeCalibration('save')",ctx);assert.equal(calls.at(-1),'/api/range-calibration/save');
 await vm.runInContext("rangeCalibration('disable')",ctx);assert.equal(calls.at(-1),'/api/range-calibration/disable');
 console.log('PASS distance UI: corrected/raw, stopped retention, errors/null/stale, 10cm input and save/disable');
})().catch(e=>{console.error(e);process.exitCode=1});
'''
subprocess.run(['node'],input=test.replace('SOURCE',json.dumps(source)),text=True,encoding='utf-8',check=True)
