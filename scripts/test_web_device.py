from pathlib import Path
import serial,subprocess,re,time,urllib.request,json,uuid
from xml.sax.saxutils import escape
r=Path(__file__).resolve().parents[1]/'reports/raw'
def net(*args):return subprocess.run(['netsh','wlan',*args],capture_output=True,text=True,errors='replace')
info=net('show','interfaces').stdout
m=re.search(r'^\s*Profile\s*:\s*(.+)$',info,re.M);assert m,'Cannot determine previous Wi-Fi profile'
previous=m[1].strip();token='AQ-Test-'+uuid.uuid4().hex[:8]
with serial.Serial('COM6',115200,timeout=.2) as s:
 s.write(b'w');raw=b'';end=time.monotonic()+2
 while time.monotonic()<end:raw+=s.read(8192)
m=re.search(rb'ssid=(\S+) password=(\S+) ip=(\S+)',raw);assert m,'AP information missing'
ssid,password,ip=[x.decode() for x in m.groups()]
xml=f'''<?xml version="1.0"?><WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1"><name>{token}</name><SSIDConfig><SSID><name>{escape(ssid)}</name></SSID></SSIDConfig><connectionType>ESS</connectionType><connectionMode>manual</connectionMode><MSM><security><authEncryption><authentication>WPA2PSK</authentication><encryption>AES</encryption><useOneX>false</useOneX></authEncryption><sharedKey><keyType>passPhrase</keyType><protected>false</protected><keyMaterial>{escape(password)}</keyMaterial></sharedKey></security></MSM></WLANProfile>'''
p=r/(token+'.xml');p.write_text(xml)
result={}
try:
 assert net('add','profile','filename='+str(p),'user=current').returncode==0
 assert net('connect','name='+token,'ssid='+ssid).returncode==0
 # Bound disconnection from the original WLAN. Always restore in finally.
 for i in range(15):
  try:
   opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
   with opener.open('http://'+ip+'/api/status',timeout=1) as x:status=json.load(x)
   assert status['role']=='P_MAIN'
   with opener.open('http://'+ip+'/',timeout=2) as x:page=x.read()
   (r/'web_live.html').write_bytes(page);(r/'web_live_status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
   result={'http':'PASS','html_bytes':len(page),'remote_age_ms':status['link_age_ms'],'child_imu_samples':status['remote']['imu_samples']};break
  except Exception as e:result={'http':'FAIL','error':str(e)};time.sleep(.5)
finally:
 restore=net('connect','name='+previous);result['restore_requested']=restore.returncode==0
 net('delete','profile','name='+token);p.unlink(missing_ok=True)
 time.sleep(3)
(r/'web_test_result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
