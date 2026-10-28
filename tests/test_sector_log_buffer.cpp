#include "sector_log_buffer.h"
#include <cassert>
#include <vector>
#include <cstdio>
int main(){
 SectorLogBuffer<4096> imu,raw;imu.reset(32);raw.reset(32);
 std::vector<uint8_t> expectedImu,expectedRaw,savedImu,savedRaw;
 unsigned writes=0;
 auto sink=[&](std::vector<uint8_t>& out,const uint8_t* p,size_t n){out.insert(out.end(),p,p+n);writes++;return true;};
 auto iSink=[&](const uint8_t* p,size_t n){return sink(savedImu,p,n);};
 auto rSink=[&](const uint8_t* p,size_t n){return sink(savedRaw,p,n);};
 // Interleave different record lengths, including records split over sectors,
 // then flush at sync/stop boundaries. Each stream must remain byte-identical.
 for(unsigned i=0;i<1000;i++){
  uint8_t a[117],b[70];for(unsigned j=0;j<117;j++)a[j]=uint8_t(i+j);for(unsigned j=0;j<70;j++)b[j]=uint8_t(i-j);
  expectedImu.insert(expectedImu.end(),a,a+117);assert(imu.append(a,117,iSink));
  for(unsigned k=0;k<3;k++){expectedRaw.insert(expectedRaw.end(),b,b+70);assert(raw.append(b,70,rSink));}
  if(i%100==99){assert(imu.flush(iSink)&&raw.flush(rSink));assert(!imu.pending()&&!raw.pending());}
 }
 assert(imu.flush(iSink)&&raw.flush(rSink));assert(savedImu==expectedImu&&savedRaw==expectedRaw&&writes<150);
 // No silent retries after a short/failed sink write; reset only for a new file.
 SectorLogBuffer<512> failing;failing.reset(32);uint8_t bytes[600]{};unsigned attempts=0;
 auto bad=[&](const uint8_t*,size_t n){assert(n==480);attempts++;return false;};
 assert(!failing.append(bytes,600,bad));assert(!failing.flush(bad));assert(!failing.append(bytes,1,bad));assert(attempts==1);
 failing.reset(32);std::vector<uint8_t> newFile;
 auto good=[&](const uint8_t* p,size_t n){newFile.insert(newFile.end(),p,p+n);return true;};
 assert(failing.append(bytes,1,good)&&failing.flush(good)&&newFile.size()==1);
 puts("PASS sector log buffering: interleaved streams, unchanged bytes, record/sector splits, sync/stop tails, sticky failure and new-file reset");
}
