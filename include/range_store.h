#pragma once
#include "range_calibration.h"
// Core 1 produces observations, core 0 owns calibration, storage and presentation.
aq::Ring<rangecal::Observation,16> rangeObservations;
std::atomic<uint32_t> rangeObservationDrops{0};
rangecal::Observation rangeLast;
rangecal::Session rangeSession;
rangecal::Profile rangeProfile;
bool rangeProfileLoaded=false,rangeRestoreError=false;
String rangeError;
void loadRangeProfile(){
 rangeProfileLoaded=false;rangeRestoreError=false;rangeProfile=rangecal::Profile{};
 FsFile dir=sd.open("/",O_RDONLY),file;char name[80];if(!dir){rangeRestoreError=true;return;}
 while(file.openNext(&dir,O_RDONLY)){
  if(file.isFile()&&file.getName(name,sizeof(name))&&String(name).startsWith("P_MAIN_RANGE_")&&String(name).endsWith(".bin")){
   rangecal::Profile p;bool ok=file.fileSize()==sizeof(p)&&file.read(&p,sizeof(p))==sizeof(p)&&rangecal::valid(p);
   if(!ok)rangeRestoreError=true;else if(!rangeProfileLoaded||p.generation>rangeProfile.generation){rangeProfile=p;rangeProfileLoaded=true;}
  }file.close();
 }dir.close();
}
bool saveRangeProfile(rangecal::Profile p){
 if(!powered||!sdCardPresent()||(!sdHealthy&&!(stopped&&!stopRequested&&!strcmp(sdReason,"STOPPED")))||dumping||stopRequested)return false;
 for(uint32_t n=rangeProfileLoaded?rangeProfile.generation+1:1;n&&n<100000;n++){
  char name[48],tmp[48];snprintf(name,sizeof(name),"P_MAIN_RANGE_%05lu.bin",(unsigned long)n);snprintf(tmp,sizeof(tmp),"P_MAIN_RANGE_%05lu.tmp",(unsigned long)n);
  if(sd.exists(name)||sd.exists(tmp))continue;
  p.generation=n;rangecal::seal(p);if(!rangecal::valid(p))return false;
  FsFile file=sd.open(tmp,O_RDWR|O_CREAT|O_EXCL);rangecal::Profile back;
  bool ok=file&&file.write(&p,sizeof(p))==sizeof(p)&&file.sync()&&file.seekSet(0)&&file.read(&back,sizeof(back))==sizeof(back)&&!memcmp(&p,&back,sizeof(p))&&rangecal::valid(back);
  file.close();if(!ok||!sd.rename(tmp,name))return false;
  rangeProfile=p;rangeProfileLoaded=true;rangeRestoreError=false;return true;
 }return false;
}
bool rangeApplied(){auto c=acquisitionSnapshot();return rangeProfileLoaded&&!rangeRestoreError&&rangecal::matches(rangeProfile,c.frequency,c.pattern);}
void rangeTick(){
 bool wasActive=rangeSession.active;
 auto config=acquisitionSnapshot();rangeSession.tick(time_us_64(),config,rangeObservationDrops.load());
 if(rangeSession.active&&!runRanging)rangeSession.fail();
 rangecal::Observation o;
 while(rangeObservations.pop(o)){
  rangeLast=o;rangeSession.feed(o);
  bool applied=rangeApplied()&&rangecal::matches(rangeProfile,o.frequency,o.pattern);
  if(sdHealthy&&!stopRequested&&!stopped){
   double value=applied?rangecal::corrected(rangeProfile,o):o.tof*aq::soundSpeed/1000000.0;
   aqbin::RangeMeasurement log{o.shot,applied?rangeProfile.generation:0,o.state,o.frequency,o.pattern,uint8_t(applied),o.tof,applied?rangeProfile.offsetUs:0,applied?rangeProfile.speed:aq::soundSpeed,o.valid()?o.tof*aq::soundSpeed/1000000.0:NAN,o.valid()&&value>=0?value:NAN};
   writeBinary(slowFile,aqbin::RANGE_MEASUREMENT,o.at,o.shot,log);
  }
 }
 if(wasActive&&!rangeSession.active)runRanging=false;
 if(rangeSession.failed&&rangeError.isEmpty())rangeError="件数・ばらつき・設定変更・欠損・期限を確認し、再測定してください";
}
bool rangeAction(const String& op,double known=0,double speed=1500){
 rangeError="";
 if(op=="status")return true;
 if(op=="cancel"){rangeSession=rangecal::Session{};runRanging=false;return true;}
 bool linked;uint16_t flags;mutex_enter_blocking(&stateMutex);linked=remoteSeenMs&&millis()-remoteSeenMs<3000;flags=remoteHealth.flags;mutex_exit(&stateMutex);
 if(runRanging||bodyActive()||i2c_mag_calibration().active||dumping||stopRequested||(linked&&(flags&aq::CALIBRATING))){rangeError="測距・個別校正・機体収録を停止してから操作してください";return false;}
 if(op=="start"){
  if(!linked){rangeError="子機との接続を確認してください";return false;}
  if(!rangeSession.start(known,speed,acquisitionSnapshot(),time_us_64(),rangeObservationDrops.load())){rangeError="既知距離は0超〜30m、音速は1300〜1700m/sで入力してください";return false;}
  runRanging=true;return true;
 }
 if(op=="save"||op=="disable"){
  auto c=acquisitionSnapshot();
  if(op=="save"&&(!rangeSession.ready||c.frequency!=rangeSession.candidate.frequency||c.pattern!=rangeSession.candidate.pattern)){rangeError="同じ周波数・パターンで31件を収集し、ばらつき条件を通過してください";return false;}
  if(op=="disable"&&!rangeProfileLoaded){rangeError="保存済み補正がありません";return false;}
  auto p=op=="save"?rangeSession.candidate:rangeProfile;if(op=="disable")p.enabled=0;
  if(!saveRangeProfile(p)){rangeError="親機SDへの保存・読戻しに失敗しました。以前の補正を維持します";return false;}
  rangeSession=rangecal::Session{};return true;
 }
 rangeError="未対応の操作です";return false;
}
String rangeJson(){
 const auto& o=rangeLast;bool applied=rangeApplied()&&rangecal::matches(rangeProfile,o.frequency,o.pattern);
 double raw=o.tof*aq::soundSpeed/1000000.0,metres=applied?rangecal::corrected(rangeProfile,o):raw;
 String s="{\"has_result\":"+String(o.at?"true":"false")+",\"shot\":"+String(o.shot)+",\"state\":"+String(o.state)+",\"age_ms\":"+(o.at?String((unsigned long)((time_us_64()-o.at)/1000)):String("null"));
 s+=",\"tof_us\":"+String((long)o.tof)+",\"raw_m\":"+(o.valid()?String(raw,4):String("null"))+",\"distance_m\":"+(o.valid()&&metres>=0?String(metres,4):String("null"));
 s+=",\"correction_applied\":"+String(applied?"true":"false")+",\"profile\":"+String(applied?rangeProfile.generation:0)+",\"accuracy_verified\":false";
 s+=",\"calibration\":{\"active\":"+String(rangeSession.active?"true":"false")+",\"ready\":"+String(rangeSession.ready?"true":"false")+",\"failed\":"+String(rangeSession.failed?"true":"false")+",\"count\":"+String(rangeSession.count)+",\"target\":31,\"rejected\":"+String(rangeSession.rejected)+",\"loaded\":"+String(rangeProfileLoaded?"true":"false")+",\"enabled\":"+String(rangeProfile.enabled?"true":"false")+",\"matches\":"+String(rangeApplied()?"true":"false")+",\"restore_error\":"+String(rangeRestoreError?"true":"false")+",\"generation\":"+String(rangeProfile.generation);
 const auto& p=(rangeSession.active||rangeSession.ready||rangeSession.failed)?rangeSession.candidate:rangeProfile;
 s+=",\"known_m\":"+String(p.knownM,4)+",\"speed_m_s\":"+String(p.speed,2)+",\"offset_us\":"+String(p.offsetUs,3)+",\"median_us\":"+String(p.medianUs,3)+",\"mad_us\":"+String(p.madUs,3)+",\"inliers\":"+String(p.samples)+",\"error\":"+ntrip::jsonString(rangeError)+"}}";return s;
}
