#pragma once
// All filesystem work runs on core 0. Tether ISR/core 1 only moves packets.
static bool localControlBusy=false,localControlDone=false;
static aq::Control localCommand,localAnswer;
static uint32_t localBegan=0;
#ifndef BOARD_PARENT
static bool bnoDispatched=false;
static uint32_t bnoRequestId=0;
#endif
static void completeControl(uint8_t error=aq::OK){localAnswer.error=error;localControlBusy=false;localControlDone=true;}
static bool beginControl(const aq::Control& c){
 if(localControlBusy || (dumping&&!(c.op>=aq::BODY_BEGIN&&c.op<=aq::BODY_CHECK)))return false;
 if(sdMounting&&!(c.op>=aq::BODY_BEGIN&&c.op<=aq::BODY_CHECK)&&c.op!=aq::INFO&&c.op!=aq::RECORD_STOP&&c.op!=aq::RECORD_START&&c.op!=aq::RECORD_NEW)return false;
 localCommand=c;localAnswer={};localAnswer.op=c.op;localControlDone=false;localControlBusy=true;localBegan=millis();
 if((c.op==aq::RECORD_START||c.op==aq::RECORD_NEW)&&c.arg!=bodycal::acknowledgeUncalibrated&&!bodyExperimentReady()){completeControl(aq::CAL_WARNING);return true;}
 if(bodyActive()&&(c.op==aq::RECORD_NEW||c.op==aq::IMU_RESET||c.op==aq::RATE_50||c.op==aq::RATE_100||(c.op>=aq::CAL_START&&c.op<=aq::CAL_END&&c.op!=aq::CAL_STATUS))){completeControl(aq::BUSY);return true;}
#ifndef BOARD_PARENT
 bnoDispatched=false;
#endif
 if(c.op==aq::RECORD_STOP || c.op==aq::RECORD_NEW){
#ifndef BOARD_PARENT
  monitorStop();monitorWeb=false;
#endif
  stopLog();
 }
 return true;
}
static void executeControl(){
 if(!localControlBusy)return;
 auto c=localCommand;
 if(c.op>=aq::BODY_BEGIN&&c.op<=aq::BODY_CHECK){
  bool ok=false;
  if(c.op==aq::BODY_STATUS||c.op==aq::BODY_CHECK)ok=true;
  else if(c.op==aq::BODY_BEGIN&&c.arg<=1)ok=bodyBegin(c.arg==1);
  else if(c.op==aq::BODY_MARK){
   uint8_t phase=c.arg&255;bool ending=c.arg&256;
   auto before=bodyCapture;
   ok=(c.arg&~0x1ffu)==0&&(!(phase==5&&ending)||bodyMotion.ready(time_us_64()))&&bodyCapture.mark(phase,ending,time_us_64());
   if(ok&&phase==5){if(ending)bodyMotionAccepted=true;else{bodyMotion.begin(time_us_64());bodyMotionAccepted=false;}}
   if(ok&&!bodyEvent(ending?3:2,phase)){bodyCapture=before;bodyAbort();ok=false;}
  }else if(c.op==aq::BODY_END){
   if(c.arg==1){bodyAbort();ok=true;}
   else if(c.arg==0)ok=bodyFinish();
  }else if(c.op==aq::BODY_IMPORT&&c.length==sizeof(bodycal::Solution)){
   bodycal::Solution s;memcpy(&s,c.data,sizeof(s));ok=bodyImport(s);
  }
  auto json=c.op==aq::BODY_CHECK?bodyCheckJson():bodyJson();
  localAnswer.arg=c.op==aq::BODY_BEGIN&&!ok?bodyLastIssues:bodyStartIssues();
  if(json.length()>sizeof(localAnswer.data)){completeControl(aq::BAD_ARGUMENT);return;}
  localAnswer.length=json.length();memcpy(localAnswer.data,json.c_str(),localAnswer.length);completeControl(ok?aq::OK:aq::BAD_ARGUMENT);return;
 }
 if(millis()-localBegan>4000){completeControl(aq::TIMEOUT);return;}
 if(c.op==aq::RECORD_STOP || c.op==aq::RECORD_NEW){
  if(stopRequested)return;
  if(c.op==aq::RECORD_NEW){bool started=startRecording();localAnswer.arg=sdMounting?1:0;completeControl(started||sdMounting?aq::OK:aq::SD_ERROR);return;}
  completeControl(strcmp(sdReason,"STOPPED")==0?aq::OK:aq::SD_ERROR);return;
 }
 if(c.op==aq::RECORD_START){if(calibrationActive){completeControl(aq::BUSY);return;}bool started=!monitorActive&&startRecording();localAnswer.arg=sdMounting?1:0;completeControl(started||sdMounting?aq::OK:aq::SD_ERROR);return;}
 if(c.op==aq::INFO){
  localAnswer.arg=imuRateHz;String s=String(sdReason);s.toCharArray((char*)localAnswer.data,sizeof(localAnswer.data));localAnswer.length=s.length();completeControl();return;
 }
#ifndef BOARD_PARENT
 if(c.op>=aq::CAL_START && c.op<=aq::CAL_END){
  if(!powered){completeControl(aq::IMU_ERROR);return;}
  if(c.op!=aq::CAL_STATUS && (!stopped || stopRequested || monitorActive || resetBno)){completeControl(aq::NOT_STOPPED);return;}
  if(!bnoDispatched){
   if(!bnoRequests.push({++bnoRequestId,c.op})){completeControl(aq::BUSY);return;}
   bnoDispatched=true;
  }
  BnoReply reply;while(bnoReplies.pop(reply)){if(reply.id==bnoRequestId){localAnswer=reply.control;if(c.op==aq::CAL_SAVE&&localAnswer.error==aq::OK&&!bodySaveDcdReceipt())localAnswer.error=aq::SD_ERROR;completeControl(localAnswer.error);return;}}
  return;
 }
 if(c.op==aq::IMU_RESET || c.op==aq::RATE_50 || c.op==aq::RATE_100){
  if(calibrationActive){completeControl(aq::BUSY);return;}
  if(!stopped || monitorActive){completeControl(aq::NOT_STOPPED);return;}
  if(c.op!=aq::IMU_RESET)imuRateHz=c.op==aq::RATE_50?50:100;
  resetBno=true;completeControl();return;
 }
 if(c.op==aq::RX_START){if(calibrationActive){completeControl(aq::BUSY);return;}monitorWeb=true;monitorStart();completeControl(monitorActive?aq::OK:aq::NOT_STOPPED);return;}
 if(c.op==aq::RX_STOP){monitorStop();monitorWeb=false;completeControl();return;}
 if(c.op==aq::RX_SAMPLE){
  int n=snprintf((char*)localAnswer.data,sizeof(localAnswer.data),"%lu,%lu,%lu,%lu,%lu,%u,%lu",(unsigned long)monitorMin,(unsigned long)(monitorBins?monitorSum/monitorBins:0),(unsigned long)monitorPeak,(unsigned long)edgeCount.load(),(unsigned long)monitorLost,unsigned(digitalRead(PIN_RX_COMP)),(unsigned long)monitorBins);
  localAnswer.length=n;localAnswer.arg=monitorActive;monitorMin=3300;monitorPeak=monitorBins=0;monitorSum=0;completeControl();return;
 }
#endif
 if(c.op==aq::FILE_LIST || c.op==aq::READ_LOG){
  if(!stopped || stopRequested || monitorActive){completeControl(aq::NOT_STOPPED);return;}
  if(c.op==aq::FILE_LIST){
   FsFile dir=sd.open("/",O_RDONLY),f;uint32_t i=0;char name[64];
   if(!dir){completeControl(aq::SD_ERROR);return;}
   while(f.openNext(&dir,O_RDONLY)){
    if(f.isFile() && f.getName(name,sizeof(name)) && (String(name).endsWith(".csv") || String(name).endsWith(".CSV") || String(name).endsWith(".bin") || String(name).endsWith(".BIN") || String(name).endsWith(".ubx") || String(name).endsWith(".rtcm3") || String(name).endsWith(".jsonl"))){
     if(i++==c.arg){localAnswer.arg=uint32_t(f.fileSize());localAnswer.length=strlen(name);memcpy(localAnswer.data,name,localAnswer.length);f.close();break;}
    }f.close();
   }dir.close();completeControl();return;
  }
  c.data[63]=0;
  if(!aq::safeFilename((const char*)c.data)){completeControl(aq::BAD_ARGUMENT);return;}
  FsFile f=sd.open((const char*)c.data,O_RDONLY);
  if(!f || !f.isFile()){completeControl(aq::NOT_FOUND);return;}
  uint64_t size=f.fileSize();
  if(size>0xffffffff || c.arg>size || !f.seekSet(c.arg)){f.close();completeControl(aq::BAD_ARGUMENT);return;}
  int n=f.read(localAnswer.data,sizeof(localAnswer.data));localAnswer.arg=uint32_t(size);f.close();
  if(n<0){completeControl(aq::SD_ERROR);return;}localAnswer.length=n;completeControl();return;
 }
 completeControl(aq::UNSUPPORTED);
}
#ifndef BOARD_PARENT
// USB diagnostics share the normal control guards and core-1 request queue.
static bool usbBnoPending=false;
static bool bnoUsb(char ch){
 static char line[24];static unsigned used=0;static bool collecting=false,overflow=false;
 if(ch=='@'&&!collecting){collecting=true;used=0;overflow=false;return true;}
 if(!collecting)return false;
 if(ch!='\n'){if(ch!='\r'){if(used+1<sizeof(line))line[used++]=ch;else overflow=true;}return true;}
 collecting=false;line[used]=0;unsigned op=0;
 bool valid=!overflow&&used==6&&!memcmp(line,"BNO 1",5)&&line[5]>='3'&&line[5]<='6';
 if(valid)op=10+unsigned(line[5]-'0');
 aq::Control c;c.op=uint8_t(op);
 bool accepted=valid&&!usbBnoPending&&!localControlBusy&&!localControlDone&&beginControl(c);
 if(accepted)usbBnoPending=true;
 Serial.printf("# BNO_USB accepted=%u op=%u\n",unsigned(accepted),op);return true;
}
#endif
static void controlTick(){
#ifndef BOARD_PARENT
 static aq::Packet active,cached;static bool have=false,cacheValid=false;
 aq::Packet p;
 if(!have && !usbBnoPending && controlIn.pop(p)){
  if(cacheValid && p.session==cached.session && p.seq==cached.seq){controlOut.push(cached);}
  else if(beginControl(aq::unpack(p))){active=p;have=true;}
 }
#endif
 executeControl();
#ifndef BOARD_PARENT
 if(usbBnoPending&&localControlDone){
  Serial.printf("# BNO_USB_RESULT op=%u error=%u data=%.*s\n",unsigned(localAnswer.op),unsigned(localAnswer.error),int(localAnswer.length),(const char*)localAnswer.data);
  usbBnoPending=false;localControlDone=false;
 }
 if(have && localControlDone){
  active.kind=aq::CONTROL_REPLY;aq::pack(active,localAnswer);
  if(controlOut.push(active)){cached=active;cacheValid=true;have=false;localControlDone=false;}
 }
#endif
}
