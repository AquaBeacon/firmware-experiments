"""Execute vendored SH-2 calibration command encoder/decoder without a device."""
from pathlib import Path
import subprocess,sys
import ziglang

root=Path(__file__).resolve().parents[1]
source=(root/'lib/Adafruit_BNO08x/src/sh2.c').read_text(encoding='utf-8')
encode=source[source.index('static int setCalConfigStart('):source.index('static void setCalConfigRx(')]
decode=source[source.index('static void getCalConfigRx('):source.index('const sh2_Op_t getCalConfigOp')]
prefix=r'''
#include "sh2.h"
#include "sh2_err.h"
#include <cassert>
#include <cstring>
#include <iostream>
constexpr unsigned COMMAND_PARAMS=9,SH2_CMD_ME_CAL=7;
struct sh2_t {struct {struct {uint8_t sensors;}calConfig;struct {uint8_t* pSensors;}getCalConfig;}opData;};
struct CommandResp_t {uint8_t r[11]{};};
uint8_t sent[9]{};int lastStatus=999,completions=0;bool wrong=false;
int sendCmd(sh2_t*,unsigned command,const uint8_t* p){assert(command==7);memcpy(sent,p,9);return 0;}
bool wrongResponse(sh2_t*,CommandResp_t*){return wrong;}
void opCompleted(sh2_t*,int status){lastStatus=status;completions++;}
'''
test=r'''
int main(){
 sh2_t hub{};uint8_t mask=255;hub.opData.getCalConfig.pSensors=&mask;
 // Independent protocol expectations from SH-2 manual Figure 56/58, not an echo of the encoder.
 hub.opData.calConfig.sensors=SH2_CAL_ACCEL|SH2_CAL_MAG|SH2_CAL_ON_TABLE;
 assert(setCalConfigStart(&hub)==0);
 const uint8_t expected[9]={1,0,1,0,0,1,0,0,0};assert(memcmp(sent,expected,9)==0);
 hub.opData.calConfig.sensors=0;assert(setCalConfigStart(&hub)==0);for(auto v:sent)assert(v==0);
 CommandResp_t response{};response.r[1]=1;response.r[2]=1;response.r[4]=1;response.r[5]=1;
 getCalConfigRx(&hub,(const uint8_t*)&response,sizeof response);assert(lastStatus==0&&mask==27);
 // Restoring a previous configuration must keep on-table and gyro/planar bits independent.
 hub.opData.calConfig.sensors=mask;setCalConfigStart(&hub);
 const uint8_t restore[9]={1,1,0,0,1,1,0,0,0};assert(memcmp(sent,restore,9)==0);
 response.r[5]=0;getCalConfigRx(&hub,(const uint8_t*)&response,sizeof response);assert(mask==11);
 response.r[0]=1;mask=99;getCalConfigRx(&hub,(const uint8_t*)&response,sizeof response);assert(lastStatus==SH2_ERR_HUB&&mask==99);
 wrong=true;int before=completions;getCalConfigRx(&hub,(const uint8_t*)&response,sizeof response);assert(completions==before&&mask==99);
 std::cout<<"PASS actual SH-2 calibration wire fields: on-table enable/readback/restore, separate gyro/planar flags, failed and unrelated responses\n";
}
'''
out=root/'reports/raw';out.mkdir(parents=True,exist_ok=True)
p=out/'test_bno_cal_config.cpp';p.write_text(prefix+encode+decode+test,encoding='utf-8')
exe=out/'test_bno_cal_config.exe'
zig=Path(ziglang.__file__).parent/('zig.exe' if sys.platform=='win32' else 'zig')
subprocess.run([str(zig),'c++','-std=c++17','-I'+str(root/'lib/Adafruit_BNO08x/src'),str(p),'-o',str(exe)],check=True)
subprocess.run([str(exe)],check=True)
