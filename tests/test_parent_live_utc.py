"""Exercise production UTC snapshot and body clock guard with a stalled core 0."""
from pathlib import Path
import subprocess, sys, ziglang

r = Path(__file__).resolve().parents[1]
main = (r/'src/main.cpp').read_text(encoding='utf-8')
snapshot = main[main.index('utcclock::Anchor utcSnapshot(){'):main.index('void utcTick(){')]
link = (r/'include/gnss_link.h').read_text(encoding='utf-8')
locked = link[link.index('bool gnssLocked('):]
body = (r/'include/body_calibration_store.h').read_text(encoding='utf-8')
guard = body[body.index('bool bodyClockReady(){'):body.index('bool bodyExperimentReady()')]
stub = r'''
#include <cassert>
#include <cstdio>
#include "utc_clock.h"
uint64_t nowUs=10000000;
uint64_t time_us_64(){return nowUs;}
int stateMutex;
void mutex_enter_blocking(int*){} void mutex_exit(int*){}
utcclock::Anchor selectedUtc;
struct GnssStatus {
 bool synchronized=true;
 uint64_t sampledUs=10000000,ppsUs=10000000,receivedUs=10010000;
 uint64_t labelledPpsUs=10000000,labelledUtcUs=1793034634000000ULL;
}gnss;
// Simulate a core 1 update while the caller obtains the mutex.
bool advanceSnapshot=false,gpsEnabled=true;
GnssStatus gnssSnapshot(){if(advanceSnapshot)nowUs=gnss.sampledUs;return gnss;}
bool spresenseGpsEnabled(){return gpsEnabled;}
struct Spr {bool recording=true,imuTimeReady=true,ppsLocked=true,synchronized=true;unsigned timeSource=1;}spr;
auto spresenseSnapshot(){return spr;}
bool spresenseFresh(const Spr&,uint64_t){return true;}
'''
checks = r'''
int main(){
 constexpr uint64_t epoch=1793034634000000ULL;
 nowUs=10400000;gnss.sampledUs=nowUs;
 // utcTick's cache expired while SD/I2C was busy; live core 1 is synchronized.
 selectedUtc={1000000,epoch-9000000,2500000,utcclock::GPS};
 auto u=utcSnapshot();assert(u.source==utcclock::GPS&&u.at(nowUs)==epoch+400000);
 assert(bodyClockReady());
 selectedUtc={};assert(bodyClockReady());
 selectedUtc={nowUs,epoch,nowUs+3000000,utcclock::RTC};assert(bodyClockReady());
 // Cross-core snapshot became newer than time captured before the read.
 nowUs=10399999;advanceSnapshot=true;assert(bodyClockReady());advanceSnapshot=false;
 // Lost PPS, stale receiver publication, invalid pairing and diagnostic exclusion
 // must not be concealed by a previously valid selected GPS cache.
 selectedUtc={10000000,epoch,11500000,utcclock::GPS};
 gnss.synchronized=false;assert(!utcSnapshot().at(nowUs)&&!bodyClockReady());gnss.synchronized=true;
 gnss.sampledUs=nowUs-100000;assert(!bodyClockReady());gnss.sampledUs=nowUs;
 gpsEnabled=false;assert(!bodyClockReady());gpsEnabled=true;
 nowUs=11500000;gnss.sampledUs=nowUs;assert(!bodyClockReady());
 nowUs=10400000;gnss.sampledUs=nowUs;gnss.receivedUs=nowUs+1;assert(!bodyClockReady());gnss.receivedUs=10010000;
 // Non-GPS sources remain available to general logging, but not axis capture.
 gpsEnabled=false;selectedUtc={10000000,epoch,12000000,utcclock::PHONE};
 assert(utcSnapshot().at(nowUs)&&!bodyClockReady());
 selectedUtc.source=utcclock::RTC;assert(utcSnapshot().at(nowUs)&&!bodyClockReady());gpsEnabled=true;
 // Spresense's independent PPS/UTC gate remains mandatory.
 spr.ppsLocked=false;assert(!bodyClockReady());spr.ppsLocked=true;
 spr.synchronized=false;assert(!bodyClockReady());spr.synchronized=true;
 spr.timeSource=3;assert(!bodyClockReady());spr.timeSource=1;assert(bodyClockReady());
 puts("PASS live parent PPS UTC: expired cache, RTC cache, cross-core time order, expiry, loss and independent Spresense guard");
}
'''
p = r/'reports/raw/test_parent_live_utc.cpp'
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(stub+locked+snapshot+guard+checks, encoding='utf-8')
zig = Path(ziglang.__file__).parent/('zig.exe' if sys.platform=='win32' else 'zig')
exe = p.with_suffix('.exe')
subprocess.run([str(zig),'c++','-std=c++17','-DBOARD_PARENT','-I'+str(r/'common'),str(p),'-o',str(exe)],check=True)
subprocess.run([str(exe)],check=True)
