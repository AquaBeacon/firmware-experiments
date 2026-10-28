#pragma once
bool rangeWebRoute(const String& path){
 if(!path.startsWith("/api/range-calibration/"))return false;
 String op=path.substring(23);double known=0,speed=1500;
 if(op.startsWith("start/")){
  int64_t v[2]{};bool ok=phone::numbers(op.substring(6).c_str(),v,2)&&v[0]>0&&v[0]<=30000&&v[1]>=1300000&&v[1]<=1700000;
  if(!ok){webReply(400,"{\"error\":\"既知距離・音速の入力を確認してください\"}");return true;}
  known=v[0]/1000.0;speed=v[1]/1000.0;op="start";
 }
 bool ok=rangeAction(op,known,speed);webReply(ok?200:409,"{\"ok\":"+String(ok?"true":"false")+",\"range_last\":"+rangeJson()+",\"error\":"+ntrip::jsonString(rangeError)+"}");return true;
}
bool rangeUsb(const char* line){
 if(strncmp(line,"RANGE ",6))return false;
 if(!strncmp(line,"RANGE config/",13)){
  int64_t v[5]{};bool ok=!runRanging&&!rangeSession.active&&phone::numbers(line+13,v,5)&&v[0]>0&&v[0]<=UINT32_MAX&&v[1]>=1&&v[1]<=5&&v[2]>=0&&v[2]<=300&&v[3]>=1&&v[3]<=4&&v[4]>=0&&v[4]<=1;
  aq::AcquisitionConfig c;if(ok){c={uint32_t(v[0]),uint16_t(v[1]),uint16_t(v[2]),uint8_t(v[3]),uint8_t(v[4])};ok=aq::validConfig(c);}
  if(ok){mutex_enter_blocking(&stateMutex);acquisitionConfig=c;mutex_exit(&stateMutex);}
  Serial.printf("{\"range_config\":true,\"ok\":%s}\n",ok?"true":"false");return true;
 }
 char op[12]{},extra;unsigned mm=0,mmps=0;int n=sscanf(line,"RANGE %11s %u %u %c",op,&mm,&mmps,&extra);
 bool valid=n==1&&strcmp(op,"start") || n==3&&!strcmp(op,"start")&&mm<=30000&&mmps>=1300000&&mmps<=1700000;
 bool ok=valid&&rangeAction(String(op),mm/1000.0,mmps/1000.0);
 Serial.println(String("{\"range_control\":true,\"ok\":")+(ok?"true":"false")+",\"error\":"+ntrip::jsonString(rangeError)+",\"range_last\":"+rangeJson()+"}");return true;
}
