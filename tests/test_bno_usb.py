"""Production USB BNO parser: bounded input, operation whitelist and arbitration."""
from pathlib import Path
import subprocess,sys,tempfile,ziglang
r=Path(__file__).resolve().parents[1]
s=(r/'include/experiment_control.h').read_text(encoding='utf-8')
s=s[s.index('static bool usbBnoPending'):s.index('static void controlTick()')].replace('#endif','')
code=r'''
#include "control.h"
#include <cassert>
#include <cstdio>
bool localControlBusy=false,localControlDone=false,allow=true;unsigned starts=0,last=0;
bool beginControl(const aq::Control& c){if(!allow)return false;starts++;last=c.op;return true;}
struct {template<class... T> void printf(const char*,T...) {}}Serial;
'''+s+r'''
void line(const char* s){while(*s)assert(bnoUsb(*s++));}
int main(){
 assert(!bnoUsb('h'));line("@BNO 14\n");assert(starts==1&&last==14&&usbBnoPending);
 line("@BNO 13\n");assert(starts==1);usbBnoPending=false;
 for(auto text:{"@BNO 12\n","@BNO 17\n","@BNO 14 x\n","@BNO 9999999999999999999999999999999999\n"}){line(text);assert(starts==1);}
 localControlBusy=true;line("@BNO 13\n");assert(starts==1);localControlBusy=false;
 localControlDone=true;line("@BNO 13\n");assert(starts==1);localControlDone=false;
 allow=false;line("@BNO 13\n");assert(!usbBnoPending);allow=true;
 line("@BNO 13\r\n");assert(starts==2&&last==13);usbBnoPending=false;
 line("@BNO 15\n");assert(last==15);usbBnoPending=false;line("@BNO 16\n");assert(last==16);
}
'''
zig=Path(ziglang.__file__).parent/('zig.exe' if sys.platform=='win32' else 'zig')
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.cpp').write_text(code,encoding='utf-8')
 subprocess.run([str(zig),'c++','-std=c++17','-include','initializer_list','-DIMU_HZ=100','-I'+str(r/'common'),str(p/'test.cpp'),'-o',str(p/'test.exe')],check=True)
 subprocess.run([str(p/'test.exe')],check=True)
print('PASS USB BNO parser and busy/pending guards')
