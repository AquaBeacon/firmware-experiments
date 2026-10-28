"""Run production immutable range-profile storage against a failing fake SD."""
from pathlib import Path
import subprocess,sys,ziglang
r=Path(__file__).resolve().parents[1]
fixture=(r/'tests/test_parent_store.cpp').read_text(encoding='utf-8').split('namespace ntrip')[0]
fixture=fixture.replace('bool exists(const char* name)', 'bool vol(){return true;} bool exists(const char* name)')
source=(r/'include/range_store.h').read_text(encoding='utf-8').split('bool rangeApplied()')[0]
stub="""
#include <cassert>
bool powered=true,sdHealthy=false,stopped=true;const char* sdReason="STOPPED";
bool dumping=false,stopRequested=false,card=true;bool sdCardPresent(){return card;}
"""
test="""
int main(){
 loadRangeProfile();assert(!rangeProfileLoaded);
 rangecal::Profile p;p.frequency=200000;p.pattern=1;p.enabled=1;p.samples=31;p.knownM=.1;p.medianUs=100;p.offsetUs=100-.1*1000000/1500;
 assert(saveRangeProfile(p)&&rangeProfile.generation==1);auto baseline=files;
 syncFailure=true;assert(!saveRangeProfile(p)&&rangeProfile.generation==1);syncFailure=false;
 shortWrite=true;assert(!saveRangeProfile(p));shortWrite=false;
 renameFailure=true;assert(!saveRangeProfile(p));renameFailure=false;
 loadRangeProfile();assert(rangeProfileLoaded&&rangeProfile.generation==1);
 assert(saveRangeProfile(p)&&rangeProfile.generation==5);files["P_MAIN_RANGE_00005.bin"][8]^=1;
 loadRangeProfile();assert(rangeRestoreError&&rangeProfile.generation==1);
 for(auto& item:baseline)assert(files[item.first]==item.second);
 p.enabled=0;assert(saveRangeProfile(p));loadRangeProfile();assert(!rangeProfile.enabled);
 card=false;assert(!saveRangeProfile(p));card=true;dumping=true;assert(!saveRangeProfile(p));
 puts("PASS actual range storage: readback, immutable save, failed sync/write/rename, CRC fallback and disable");
}
"""
path=r/'reports/raw/test_range_store.cpp';path.write_text(fixture+stub+source+test,encoding='utf-8')
zig=Path(ziglang.__file__).parent/('zig.exe' if sys.platform=='win32' else 'zig')
subprocess.run([str(zig),'c++','-std=c++17','-DIMU_HZ=100','-I'+str(r/'common'),str(path),'-o',str(path.with_suffix('.exe'))],check=True)
subprocess.run([str(path.with_suffix('.exe'))],check=True)
