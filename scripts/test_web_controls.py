"""Exercise the actual AP and tether control API; restore WLAN and stop TX in finally."""
from pathlib import Path
import serial,subprocess,re,time,urllib.request,json,uuid,zlib
from xml.sax.saxutils import escape
r=Path(__file__).resolve().parents[1]/'reports/raw'
def net(*args):return subprocess.run(['netsh','wlan',*args],capture_output=True,text=True,errors='replace')
info=net('show','interfaces').stdout
m=re.search(r'^\s*Profile\s*:\s*(.+)$',info,re.M);assert m,'Cannot determine previous Wi-Fi profile'
previous=m[1].strip();token='AQ-Control-'+uuid.uuid4().hex[:8]
xml=f'''<?xml version="1.0"?><WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1"><name>{token}</name><SSIDConfig><SSID><name>AquaBeacon-MAIN</name></SSID></SSIDConfig><connectionType>ESS</connectionType><connectionMode>manual</connectionMode><MSM><security><authEncryption><authentication>WPA2PSK</authentication><encryption>AES</encryption><useOneX>false</useOneX></authEncryption><sharedKey><keyType>passPhrase</keyType><protected>false</protected><keyMaterial>ChangeMe-Example-Only</keyMaterial></sharedKey></security></MSM></WLANProfile>'''
p=r/(token+'.xml');p.write_text(xml,encoding='utf-8');opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));results={}
def req(path,post=False):
 q=urllib.request.Request('http://192.168.4.1'+path,method='POST' if post else 'GET',headers={'X-Aqua-Control':'1'} if post else {})
 with opener.open(q,timeout=9) as response:return json.load(response)
def cmd(target,op,arg=0,name=''):
 v=req(f'/api/control/{target}/{op}/{arg}'+('/'+name if name else ''),True)
 assert not v['error'],(target,op,v);return v
def log(message):print(message,flush=True)
try:
 assert net('add','profile','filename='+str(p),'user=current').returncode==0
 assert net('connect','name='+token,'ssid=AquaBeacon-MAIN').returncode==0
 for i in range(20):
  try:initial=req('/api/status');break
  except Exception:time.sleep(.5)
 else:raise RuntimeError('AP not reachable')
 log('AP connected')
 for target in ['p','c']:
  results[target+'_info']=cmd(target,1)
  cmd(target,2);cmd(target,3)
 log('Parent/child stop and resume acknowledged')
 req('/api/range/start',True);time.sleep(2.5);results['ranging']=req('/api/status');assert results['ranging']['ranging']
 req('/api/range/stop',True);assert not req('/api/status')['ranging'];log('Range start/stop PASS')
 cmd('c',2);cmd('c',6);time.sleep(2);assert cmd('c',1)['arg']==50;cmd('c',3);time.sleep(2);cmd('c',2)
 cmd('c',7);time.sleep(2);assert cmd('c',1)['arg']==100;cmd('c',3);time.sleep(2);cmd('c',2);log('50/100 Hz configuration PASS')
 cmd('c',10);time.sleep(.5);sample=cmd('c',12);assert sample['arg']==1 and sample['length'];results['rx_sample']=bytes.fromhex(sample['hex']).decode();cmd('c',11);log('ADC monitor control PASS')
 for target in ['p','c']:
  cmd(target,2);files=[]
  for index in range(500):
   v=cmd(target,8,index)
   if not v['length']:break
   files.append((bytes.fromhex(v['hex']).decode(),v['arg']))
  results[target+'_files']=files
  prefix='P_MAIN_HEALTH_RANGE' if target=='p' else 'C_MAIN_HEALTH_RANGE'
  name,size=sorted((f for f in files if f[0].startswith(prefix)),reverse=True)[0]
  data=bytearray()
  while len(data)<size:
   v=cmd(target,9,len(data),name);block=bytes.fromhex(v['hex']);assert block and v['arg']==size;data+=block
  assert len(data)==size
  for line in data.splitlines()[1:]:
   body,crc=line.rsplit(b',',1);assert zlib.crc32(body)==int(crc,16)
  (r/('web_download_'+target+'.csv')).write_bytes(data);results[target+'_download']={'name':name,'bytes':size,'crc':'PASS'};log(target+' file list/download CRC PASS')
 results['result']='PASS'
finally:
 try:
  req('/api/range/stop',True)
  cmd('c',11)
  for target in ['p','c']:cmd(target,3)
  results['final']=req('/api/status')
 except Exception as e:results['cleanup_error']=str(e)
 net('connect','name='+previous);net('delete','profile','name='+token);p.unlink(missing_ok=True)
 (r/'web_controls_result.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
