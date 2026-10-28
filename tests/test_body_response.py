"""Run the actual BODY control branch with the actual in-memory SD store."""
from pathlib import Path
import subprocess,sys,ziglang
r=Path(__file__).resolve().parents[1]
stub=(r/'tests/test_body_store.cpp').read_text().split('int main(){')[0]
s=(r/'include/experiment_control.h').read_text()
branch=s[s.index(' if(c.op>=aq::BODY_BEGIN'):s.index(' if(millis()-localBegan>')]
handler='aq::Control localAnswer;void completeControl(uint8_t e){localAnswer.error=e;}void handle(aq::Control c){localAnswer={};'+branch+'}\n'
checks=r'''
int main(){
 bodyDcdGeneration=1;stopped=true;runRanging=true;
 aq::Control c;c.op=aq::BODY_BEGIN;handle(c);
 assert(localAnswer.error==aq::BAD_ARGUMENT);assert(localAnswer.arg==(bodyissue::record|bodyissue::ranging));assert(files.empty());assert(localAnswer.length<=104);
 c.op=aq::BODY_CHECK;handle(c);assert(localAnswer.error==0&&localAnswer.length<=104);std::string d((char*)localAnswer.data,localAnswer.length);assert(d.find("\"x\":36")!=d.npos);
 stopped=false;runRanging=false;c.op=aq::BODY_BEGIN;handle(c);assert(localAnswer.error==0&&bodyActive());assert(localAnswer.arg==bodyissue::active);
 c.op=aq::BODY_MARK;c.arg=1;handle(c);assert(!localAnswer.error);fakeNow+=3000000;c.arg=257;handle(c);assert(localAnswer.error);
 fakeNow+=2000000;handle(c);assert(!localAnswer.error&&bodyCapture.mask==1);
 c.op=aq::BODY_END;c.arg=0;handle(c);assert(localAnswer.error&&bodyActive());c.arg=1;handle(c);assert(!localAnswer.error&&!bodyActive()&&bodyRunState==3);
 stopped=true;c.op=aq::BODY_BEGIN;c.arg=1;handle(c);assert(localAnswer.error&&localAnswer.arg==(bodyissue::record|bodyissue::axes));
 c.op=aq::BODY_STATUS;handle(c);assert(!localAnswer.error&&localAnswer.length<=104);
 puts("PASS production BODY control responses: refusal mask, no file on rejection, bounded status/diagnostics, phase time guard, incomplete finish and abort");
}
'''
p=r/'reports/raw/test_body_response.cpp';p.write_text(stub+handler+checks)
zig=Path(ziglang.__file__).parent/('zig.exe' if sys.platform=='win32' else 'zig')
exe=p.with_suffix('.exe');subprocess.run([str(zig),'c++','-std=c++17','-DIMU_HZ=100','-I'+str(r/'common'),'-I'+str(r/'include'),str(p),'-o',str(exe)],check=True)
subprocess.run([str(exe)],check=True)
