#pragma once
#include "ranging.h"
#include <algorithm>
#include <cmath>
namespace rangecal {
constexpr unsigned target=31;
constexpr uint64_t timeoutUs=180000000;
struct Observation {
 uint64_t at=0;uint32_t shot=0,state=0,frequency=0;uint8_t pattern=0;int64_t tof=0;uint64_t planned=0;
 bool valid()const{return (state==2||state==3)&&tof>=0&&tof<=int64_t(aq::windowUs);}
};
#pragma pack(push,1)
struct Profile {
 uint32_t magic=0x5243414c;uint16_t version=1,bytes=sizeof(Profile);
 uint32_t generation=0,frequency=0;uint8_t pattern=0,enabled=0;uint16_t samples=0;
 double knownM=0,speed=1500,offsetUs=0,medianUs=0,madUs=0;
 uint32_t crc=0;
};
#pragma pack(pop)
inline void seal(Profile& p){p.crc=aq::crc32(&p,sizeof(p)-4);}
inline bool valid(const Profile& p){return p.magic==0x5243414c&&p.version==1&&p.bytes==sizeof(p)&&p.generation&&
 p.crc==aq::crc32(&p,sizeof(p)-4)&&p.enabled<=1&&p.pattern<=1&&aq::supportedFrequency(p.frequency)&&
 std::isfinite(p.knownM)&&p.knownM>0&&p.knownM<=30&&std::isfinite(p.speed)&&p.speed>=1300&&p.speed<=1700&&
 std::isfinite(p.offsetUs)&&std::abs(p.offsetUs)<=30000&&std::isfinite(p.medianUs)&&p.medianUs>=0&&p.medianUs<=aq::windowUs&&
 std::isfinite(p.madUs)&&p.madUs>=0&&p.madUs<=50&&p.samples>=25&&p.samples<=target;}
inline bool matches(const Profile& p,uint32_t hz,uint8_t pattern){return p.enabled&&p.frequency==hz&&p.pattern==pattern;}
inline double corrected(const Profile& p,const Observation& o){return (o.tof-p.offsetUs)*p.speed/1000000.0;}
struct Session {
 bool active=false,ready=false,failed=false;uint64_t began=0;unsigned count=0,rejected=0;uint32_t drops=0;
 int64_t values[target]{};Profile candidate;
 bool start(double known,double speed,const aq::AcquisitionConfig& c,uint64_t now,uint32_t lost){
  if(!std::isfinite(known)||known<=0||known>30||!std::isfinite(speed)||speed<1300||speed>1700||!aq::validConfig(c))return false;
  *this=Session{};active=true;began=now;drops=lost;candidate.knownM=known;candidate.speed=speed;candidate.frequency=c.frequency;candidate.pattern=c.pattern;return true;
 }
 void fail(){active=false;ready=false;failed=true;}
 void tick(uint64_t now,const aq::AcquisitionConfig& c,uint32_t lost){if(active&&(now<began||now-began>=timeoutUs||c.frequency!=candidate.frequency||c.pattern!=candidate.pattern||lost!=drops))fail();}
 void feed(const Observation& o){
  if(!active||o.at<began||(o.planned&&o.planned<began))return;
  if(o.frequency!=candidate.frequency||o.pattern!=candidate.pattern){fail();return;}
  if(!o.valid()){rejected++;return;}
  values[count++]=o.tof;if(count<target)return;
  // A single known distance estimates a fixed offset only, never propagation speed.
  std::sort(values,values+count);double median=values[count/2],dev[target];
  for(unsigned i=0;i<count;i++)dev[i]=std::abs(values[i]-median);
  std::sort(dev,dev+count);double mad=dev[count/2];unsigned inliers=0;
  const double limit=std::max(20.0,3*mad);
  for(unsigned i=0;i<count;i++)if(std::abs(values[i]-median)<=limit)inliers++;
  active=false;if(inliers<25||mad>50){failed=true;return;}
  candidate.enabled=1;candidate.samples=inliers;candidate.medianUs=median;candidate.madUs=mad;
  candidate.offsetUs=median-candidate.knownM*1000000.0/candidate.speed;ready=true;
 }
};
}
