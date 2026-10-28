#include "range_calibration.h"
#include <cassert>
#include <limits>
#include <iostream>
int main(){
 rangecal::Session s;aq::AcquisitionConfig c{200000,3,30,1,1};uint64_t t=0x100000000ULL;
 assert(!s.start(0,1500,c,t,0));assert(!s.start(.1,NAN,c,t,0));
 assert(s.start(.1,1500,c,t,0));
 s.feed({t-1,1,2,c.frequency,c.pattern,100});assert(!s.count);
 s.feed({t+1,1,2,c.frequency,c.pattern,100,t-1});assert(!s.count);
 s.feed({t,1,4,c.frequency,c.pattern,100});assert(s.rejected==1&&!s.count);
 for(unsigned i=0;i<31;i++)s.feed({t+i,2+i,2,c.frequency,c.pattern,i<5?1000:100});
 assert(s.ready&&!s.active&&s.candidate.samples==26&&s.candidate.medianUs==100&&s.candidate.madUs==0);
 auto p=s.candidate;p.generation=1;rangecal::seal(p);assert(rangecal::valid(p));
 rangecal::Observation o{t,1,2,c.frequency,c.pattern,100};assert(std::abs(rangecal::corrected(p,o)-.1)<1e-10);
 assert(rangecal::matches(p,200000,1)&&!rangecal::matches(p,100000,1)&&!rangecal::matches(p,200000,0));
 p.crc++;assert(!rangecal::valid(p));p.crc--;p.speed=NAN;rangecal::seal(p);assert(!rangecal::valid(p));
 s.start(.1,1500,c,t,0);for(unsigned i=0;i<31;i++)s.feed({t+i,i,3,c.frequency,c.pattern,int64_t(i*100)});assert(s.failed&&!s.ready);
 s.start(.1,1500,c,t,0);s.tick(t+rangecal::timeoutUs,c,0);assert(s.failed);
 s.start(.1,1500,c,t,0);s.tick(t,c,1);assert(s.failed);
 s.start(.1,1500,c,t,0);auto different=c;different.pattern=0;s.tick(t,different,0);assert(s.failed);
 s.start(.1,1500,c,t,0);s.feed({t,1,3,100000,1,100});assert(s.failed);
 assert((!rangecal::Observation{t,1,4,200000,1,0}.valid()));
 std::cout<<"PASS range calibration: one-point offset, outlier rejection, spread, nonfinite, CRC, configuration, loss and timeout\n";
}
