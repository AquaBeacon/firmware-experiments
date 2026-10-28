#include "bno_calibration.h"
#include "control.h"
#include <cassert>
#include <iostream>
#include <limits>
void feed(aq::BnoCalibration& c,uint64_t t,unsigned a=2,unsigned g=1,unsigned m=2,float rate=0){
 c.event(0,a,t);c.event(1,g,t);c.event(2,m,t);c.gyro(rate,0,0,t);c.tick(t);
}
int main(){
 aq::BnoCalibration c;const uint64_t t=0x100000000ULL;
 c.start(t,7);assert(c.active&&!c.saved&&c.previousMask==7&&!c.ready(t));
 // Rest first, then magnetic rotations; low gyro status is still displayed as low.
 for(unsigned n=0;n<30;n++){feed(c,t+n*100000);assert(!c.ready(t+n*100000));assert(!c.gyroRestDone);}
 feed(c,t+3000000);assert(c.gyroRestDone&&c.restMs(t+3000000)==3000&&!c.ready(t+3000000));
 for(unsigned n=31;n<=40;n++)feed(c,t+n*100000,2,1,2,.3f);
 assert(c.ready(t+4000000)&&c.gyroRestDone&&c.accuracy[1]==1);
 feed(c,t+4100000,2,0);assert(!c.ready(t+4100000)&&c.gyroRestDone);
 for(unsigned n=42;n<=82;n++)feed(c,t+n*100000);
 assert(c.ready(t+8200000));c.tick(t+8700000);assert(!c.goodSince&&!c.gyroRestDone&&!c.ready(t+8700000));
 feed(c,t+8800000,2,1,2,.3f);assert(!c.gyroReady(t+8800000));
 c.start(t,21);for(unsigned n=0;n<=100;n++){feed(c,t+n*100000,2,1,2,.3f);assert(!c.ready(t+n*100000));}
 c.start(t,7);for(unsigned n=0;n<=40;n++)feed(c,t+n*100000,2,0);
 assert(c.restMs(t+4000000)==3000&&c.gyroRestDone&&!c.ready(t+4000000));
 // A medium-quality gyro needs no host rest fallback; all data must stay fresh.
 c.start(t,7);for(unsigned n=0;n<10;n++){feed(c,t+n*100000,2,2,2,.3f);assert(!c.ready(t+n*100000));}
 feed(c,t+1000000,2,2,2,.3f);assert(c.ready(t+1000000));
 feed(c,t+1100000,1,2);assert(!c.ready(t+1100000)&&!c.goodSince);
 feed(c,t+1200000,2,2,1);assert(!c.ready(t+1200000));
 feed(c,t+1300000,2,3,2,std::numeric_limits<float>::quiet_NaN());assert(!c.ready(t+1300000));
 feed(c,t+1400000,2,3,2,std::numeric_limits<float>::infinity());assert(!c.ready(t+1400000));
 // A status alone, without the corresponding vector, cannot create gyro evidence.
 c.start(t,7);for(unsigned n=0;n<=40;n++){for(unsigned i=0;i<3;i++)c.event(i,3,t+n*100000);c.tick(t+n*100000);}
 assert(!c.ready(t+4000000)&&!c.gyroRestDone);
 c.start(t,7);feed(c,t);feed(c,t+500000);assert(c.restMs(t+500000)==0);
 feed(c,t+400000);assert(c.restMs(t+400000)==0&&!c.gyroRestDone);
 c.start(t,7);feed(c,t);for(unsigned n=1;n<=40;n++){c.event(1,1,t+n*100000);c.gyro(0,0,0,t+n*100000);c.tick(t+n*100000);}
 assert(c.gyroRestDone&&!c.ready(t+4000000));
 c.saved=true;c.clear();assert(!c.active&&!c.saved&&!c.gyroRestDone&&!c.fresh(0,t));
 c.start(t,1);assert(!c.expired(t+599999999));assert(c.expired(t+600000000));
 c.start(t+600000001,7);assert(!c.saved&&!c.goodSince&&!c.gyroRestDone&&!c.fresh(2,t+600000001));
 aq::Packet p;aq::Control in;in.op=aq::CAL_SAVE;in.error=aq::CAL_NOT_READY;aq::pack(p,in);auto out=aq::unpack(p);assert(out.op==aq::CAL_SAVE && out.error==aq::CAL_NOT_READY);
 assert((aq::CALIBRATING & (3<<12))==0);
 std::cout<<"PASS BNO gyro rest fallback, sequential magnetic motion, low/zero status, gaps, nonfinite/missing data, continuous readiness, session reset and 64-bit time\n";
}
