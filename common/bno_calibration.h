#pragma once
#include <stdint.h>
#include <cmath>
namespace aq {
// Sensor-reported accuracy is a progress indicator, not measured angular accuracy.
struct BnoCalibration {
 bool active=false,saved=false,gyroFinite=false,gyroRestDone=false;
 uint8_t accuracy[3]{},previousMask=0;
 uint64_t seen[3]{},started=0,goodSince=0,gyroAt=0,stillSince=0;
 static constexpr uint64_t lifetimeUs=600000000, freshUs=500000, settleUs=1000000, stillUs=3000000;
 // Application-level rest hint, not CEVA's internal calibration or an accuracy limit.
 static constexpr float stillRadS=0.05f;
 void clear(){*this=BnoCalibration{};}
 void start(uint64_t now,uint8_t mask){clear();active=true;started=now;previousMask=mask;}
 void event(unsigned sensor,uint8_t status,uint64_t now){if(sensor<3){accuracy[sensor]=status&3;seen[sensor]=now;}}
 bool fresh(unsigned sensor,uint64_t now)const{return sensor<3 && seen[sensor] && now>=seen[sensor] && now-seen[sensor]<freshUs;}
 void gyro(float x,float y,float z,uint64_t now){
  if(!active)return;
  if(!gyroAt||now<gyroAt||now-gyroAt>=freshUs){stillSince=0;gyroRestDone=false;}
  gyroAt=now;gyroFinite=std::isfinite(x)&&std::isfinite(y)&&std::isfinite(z);
  // Rest is observed from the vector even while the hub still reports unreliable.
  // Saving independently requires nonzero sensor accuracy in gyroReady().
  if(!gyroFinite||!fresh(1,now)){stillSince=0;gyroRestDone=false;return;}
  if(x*x+y*y+z*z<=stillRadS*stillRadS){
   if(!stillSince)stillSince=now;
   if(now-stillSince>=stillUs)gyroRestDone=true;
  }else stillSince=0; // Keep completed rest through the subsequent magnetic rotations.
 }
 uint32_t restMs(uint64_t now)const{
  if(!active||!fresh(1,now)||!gyroFinite)return 0;
  if(gyroRestDone)return uint32_t(stillUs/1000);
  return stillSince&&now>=stillSince?uint32_t((now-stillSince<stillUs?now-stillSince:stillUs)/1000):0;
 }
 bool gyroReady(uint64_t now)const{return fresh(1,now)&&gyroAt==seen[1]&&gyroFinite&&accuracy[1]>=1&&(accuracy[1]>=2||gyroRestDone);}
 bool good(uint64_t now)const{return fresh(0,now)&&accuracy[0]>=2&&fresh(2,now)&&accuracy[2]>=2&&gyroReady(now);}
 void tick(uint64_t now){
  if(!active||!fresh(1,now)||!gyroFinite){stillSince=0;gyroRestDone=false;}
  if(!active||!good(now))goodSince=0;else if(!goodSince)goodSince=now;
 }
 bool ready(uint64_t now)const{return active && good(now) && goodSince && now>=goodSince && now-goodSince>=settleUs;}
 bool expired(uint64_t now)const{return active && now-started>=lifetimeUs;}
};
}
