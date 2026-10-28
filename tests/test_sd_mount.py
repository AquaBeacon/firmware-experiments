"""Run the production mount state machine, never Arduino or actual SD writes."""
from pathlib import Path
import subprocess,sys,ziglang
r=Path(__file__).resolve().parents[1]
fixture=(r/'tests/test_parent_store.cpp').read_text(encoding='utf-8').split('namespace ntrip')[0]
fixture=fixture.replace('} sd;', 'bool cardBegin(int){calls++;return !cardFailure;}bool volumeBegin(){calls++;return true;}void primeAllocationHint(unsigned){calls++;}void end(){}unsigned sdErrorCode(){return 0;}unsigned sdErrorData(){return 0;} } sd;')
fixture=fixture.replace('struct {\n bool exists', 'unsigned calls=0;bool cardFailure=false;\nstruct {\n bool exists')
main=(r/'src/main.cpp').read_text(encoding='utf-8')
source=main[main.index('bool mountSd(){'):main.index('bool startRecording(){')]
stub=r'''
#include <cassert>
#include "binary_log.h"
#include "sd_io_deadline.h"
constexpr int O_WRONLY=16,SHARED_SPI=0,PIN_SD_CS=13,PIN_SD_SCK=10,PIN_SD_MOSI=11,PIN_SD_MISO=12,SD_SPI_MHZ=1;
#define SD_SCK_MHZ(x) (x)
int sdSpi=0;int SdSpiConfig(int,int,int,int*){return 0;}
struct {void setSCK(int){}void setTX(int){}void setRX(int){}}SPI1;
uint64_t now=100;uint64_t time_us_64(){return now;}unsigned millis(){return now/1000;}
bool sdMounting=false,powered=true,dumping=false,stopRequested=false,sdHealthy=false,captureEnabled=true,stopped=false,pauseAck=false,allowed=true;
unsigned sdMountStep=0,sdLogSeed=0,sdMountSequence=0,startupStage=0,sdMountElapsedMs=0;
uint64_t sdMountBegan=0;uint32_t sessionId=777,rawRows=0,rows=0,durableRows=0,lastSyncMs=0;const char* sdReason="NOT_STARTED";
FsFile logFile,slowFile,rawFile,observationFile;char logName[64]{},slowName[64]{},rawName[64]{},observationName[64]{};
struct SdMountScope{};bool sdCardPresent(){return true;}bool sdInitAllowed(){return allowed;}
void resetSdWriteBuffers(){}
struct {bool expired=false;}sdIoDeadline;
void failSd(const char* s,unsigned=0,unsigned=0){sdMounting=false;sdHealthy=false;sdReason=s;}
bool openUnique(FsFile&,char*,char,unsigned){calls++;return true;}
void closeGnssFiles(){}bool openGnssPart(unsigned){calls++;return true;}
void loadMagCalibration(){calls++;}void loadParentCalibration(){calls++;}void loadRangeProfile(){calls++;}void loadBodyCalibration(){calls++;}
namespace ntrip{void bootSettings(){calls++;}}
bool gnssRecording=false,parentCalibrationLoaded=false;struct {unsigned generation=1;}parentCalibration;
template<class T>bool writeBinary(FsFile&,unsigned,uint64_t,unsigned,const T&){calls++;return true;}
struct {unsigned count=0;void mounted(unsigned){count++;}}sdRecovery;
'''
test=r'''
int main(){
 assert(!mountSd()&&sdMounting&&calls==0&&!captureEnabled);
 unsigned stages=0;while(sdMounting){unsigned old=calls;sdMountTick();assert(calls-old<=2);assert(++stages<20);}
 assert(sdHealthy&&!stopped&&captureEnabled&&sdRecovery.count==1&&stages==15);
 sdHealthy=false;assert(!mountSd());sdMountTick();cancelSdMount();assert(!sdMounting&&stopped&&!strcmp(sdReason,"STOPPED"));
 unsigned count=calls;sdMountTick();assert(calls==count);
 cardFailure=true;assert(!mountSd());sdMountTick();assert(!sdMounting&&!sdHealthy&&!strcmp(sdReason,"MOUNT_FAILED"));cardFailure=false;
 assert(!mountSd());now+=20000000;sdMountTick();assert(!sdMounting&&!strcmp(sdReason,"INIT_TIMEOUT"));
 assert(!mountSd());allowed=false;sdIoDeadline.expired=true;sdMountTick();assert(!sdMounting&&!strcmp(sdReason,"INIT_TIMEOUT"));
 puts("PASS actual SD mount: deferred start, one phase/tick, commit only after all stages, cancel, failed card, total and I/O timeout");
}
'''
out=r/'reports/raw/test_sd_mount.cpp';out.write_text(fixture+stub+source+test,encoding='utf-8')
zig=Path(ziglang.__file__).parent/('zig.exe' if sys.platform=='win32' else 'zig')
subprocess.run([str(zig),'c++','-std=c++17','-DBOARD_PARENT','-DIMU_HZ=50','-I'+str(r/'common'),str(out),'-o',str(out.with_suffix('.exe'))],check=True)
subprocess.run([str(out.with_suffix('.exe'))],check=True)
