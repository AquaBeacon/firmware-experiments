"""Compile actual binary write/buffer/stop functions and verify durable tails."""
from pathlib import Path
import subprocess, sys, ziglang
r=Path(__file__).resolve().parents[1]
s=(r/'src/main.cpp').read_text(encoding='utf-8')
buffers=s[s.index('#ifndef BOARD_PARENT\nSectorLogBuffer'):s.index('constexpr size_t LOG_NAME_CAP')]
write=s[s.index('bool writeBinary(FsFile&'):s.index('template<class T> bool writeBinary')]
stop=s[s.index('void finishStop(){'):s.index('#ifdef AQ_SD_RECOVERY_TEST\n// Diagnostic builds')]
stub=r'''
#include "binary_log.h"
#include "sector_log_buffer.h"
#include <vector>
#include <atomic>
#include <cassert>
#include <algorithm>
#include <cstdio>
using std::max;
struct FsFile {
 std::vector<uint8_t> bytes=std::vector<uint8_t>(32);bool closed=false,bad=false;
 explicit operator bool()const{return !closed;}
 size_t write(const void* p,size_t n){if(bad)return 0;auto b=(const uint8_t*)p;bytes.insert(bytes.end(),b,b+n);return n;}
 bool getWriteError(){return bad;}bool sync(){return !bad;}void close(){closed=true;}
}logFile,rawFile,slowFile,observationFile;
struct {unsigned sdErrorCode(){return 0;}unsigned sdErrorData(){return 0;}}sd;
uint64_t ticks=1;uint64_t time_us_64(){return ticks++;}
uint32_t maxWriteUs=0;bool stopped=false,stopRequested=true,sdHealthy=true;
const char* sdReason="NONE";std::atomic<uint32_t> rows{0},durableRows{0};unsigned failures=0;
void failSd(const char* reason,unsigned=0,unsigned=0){failures++;sdReason=reason;sdHealthy=false;}
'''
checks=r'''
int main(){
 resetSdWriteBuffers();aqbin::Imu imu{};aqbin::Bno raw{};
 for(unsigned i=0;i<19;i++){
  imu.index=i;assert(writeBinary(logFile,aqbin::IMU,i,i,&imu,sizeof(imu)));rows++;
  raw.sequence=i;assert(writeBinary(rawFile,aqbin::BNO,i,i,&raw,sizeof(raw)));
 }
 assert(logFile.bytes.size()==32&&rawFile.bytes.size()==32);assert(imuWriteBuffer.pending()&&rawWriteBuffer.pending());
 finishStop();assert(stopped&&!stopRequested&&!sdHealthy&&durableRows==19&&!failures);
 assert(logFile.closed&&rawFile.closed&&!imuWriteBuffer.pending()&&!rawWriteBuffer.pending());
 assert(logFile.bytes.size()==32+19*(24+sizeof(imu)));assert(rawFile.bytes.size()==32+19*(24+sizeof(raw)));
 for(unsigned i=0;i<19;i++){
  aqbin::RecordHeader h;size_t offset=32+i*(24+sizeof(imu));memcpy(&h,logFile.bytes.data()+offset,24);
  assert(h.sequence==i&&aqbin::valid(h,logFile.bytes.data()+offset+24));
 }
 logFile=FsFile{};rawFile=FsFile{};slowFile=FsFile{};observationFile=FsFile{};resetSdWriteBuffers();sdHealthy=true;
 assert(writeBinary(logFile,aqbin::IMU,1,1,&imu,sizeof(imu)));logFile.bad=true;finishStop();
 assert(failures==1&&!sdHealthy&&std::string(sdReason)=="STOP_SYNC_FAILED");
 puts("PASS actual binary buffering and safe stop: exact records/CRC, tail flush before close, durable count and failed tail refuses success");
}
'''
stub=stub.replace('#include <cstdio>','#include <cstdio>\n#include <string>')
out=r/'reports/raw/test_sd_write_buffer.cpp';out.write_text(stub+buffers+write+stop+checks,encoding='utf-8')
zig=Path(ziglang.__file__).parent/('zig.exe' if sys.platform=='win32' else 'zig')
subprocess.run([str(zig),'c++','-std=c++17','-DIMU_HZ=100','-I'+str(r/'common'),str(out),'-o',str(out.with_suffix('.exe'))],check=True)
subprocess.run([str(out.with_suffix('.exe'))],check=True)
