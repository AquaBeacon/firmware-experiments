"""Exercise real MainCore staging/write and formatter/stop paths without hardware."""
from pathlib import Path
import subprocess,sys,ziglang
r=Path(__file__).resolve().parents[1]
source=(r/'firmware/spresense/logger/logger.ino').read_text(encoding='utf-8')
write_fn=source[source.index('bool writeComplete('):source.index('bool flushLog(')]
formatter_fn=source[source.index('void serviceFormatter()'):source.index('bool openLogs()')]
stub=r'''
#include <atomic>
#include <vector>
#include <cassert>
#include <cstdio>
#include <cerrno>
#include "ImuBatch.h"
#include "sd_sector_write.h"
struct {void kick(){}} Watchdog;
struct {template<class... T>void printf(const char*,T...){}} Serial;
uint64_t maxSdWriteUs=0,position=0;uint32_t now=0;
uint32_t micros(){return ++now;}uint32_t millis(){return ++now;}void reportSdSpace(){}
off_t lseek(int,off_t,int){return position;}
std::vector<uint8_t> bytes;bool shortWrite=false,interruptOnce=false,writeFails=false;int calls=0;const char* original=nullptr;
long write(int,const void* p,size_t n){
 assert(uintptr_t(p)%32==0 && p!=original && n<=512-position%512);++calls;
 if(interruptOnce){interruptOnce=false;errno=EINTR;return -1;}
 if(writeFails){errno=ETIMEDOUT;return -1;}
 if(shortWrite)n=std::min(n,size_t(17));
 auto b=static_cast<const uint8_t*>(p);bytes.insert(bytes.end(),b,b+n);position+=n;return n;
}
'''
middle=r'''
using ImuRow=aqimu::Row;
struct {
 ImuRow data[1024]{};std::atomic<unsigned> head{0},tail{0};
 bool pop(ImuRow& r){if(head==tail)return false;r=data[tail];tail=(tail+1)%1024;return true;}
 void feed(unsigned n){while(n--){data[head].seq=head;head=(head+1)%1024;}}
} imuQueue;
aqimu::Batch buffers[2]{};aqimu::Batch *batchBuffers=buffers,*batch=buffers,*sent=nullptr;
bool workerOk=true,workerPending=false,recording=true,sdReady=true,responseReady=false;
uint32_t queueDrops=0,workerErrors=0,maxFormatterMs=0,workerBatches=0,workerId=0,workerStarted=0,sdRows=0;int imuFile=1;
struct {
 int Send(int,void* p,int){sent=static_cast<aqimu::Batch*>(p);return 0;}
 int Recv(int8_t* id,uint32_t* response,int){if(!responseReady)return -1;responseReady=false;*id=11;*response=sent->id;return 0;}
} MP;
void failWorker(const char*,int){++workerErrors;workerOk=workerPending=false;}
void failSd(const char*,int){sdReady=false;recording=false;}
void complete(){assert(sent&&aqimu::formatBinary(*sent));responseReady=true;serviceFormatter();}
'''
# Forward declare because the completion helper calls the production function.
middle=middle.replace('void complete()', 'void serviceFormatter();\nvoid complete()')
checks=r'''
int main(){
 char raw[2001];for(unsigned i=0;i<sizeof(raw);i++)raw[i]=char(i*37);original=raw;
 for(unsigned offset=0;offset<512;offset++){
  position=offset;bytes.clear();shortWrite=offset%2;interruptOnce=true;
  assert(writeComplete(1,raw,sizeof(raw)) && bytes.size()==sizeof(raw)&&!memcmp(bytes.data(),raw,sizeof(raw)));
 }
 writeFails=true;position=0;calls=0;assert(!writeComplete(1,raw,1000)&&errno==ETIMEDOUT&&calls==1);writeFails=false;
 shortWrite=false;position=512;bytes.clear();
 imuQueue.feed(31);serviceFormatter();assert(!workerPending&&!sent&&imuQueue.tail==0);
 imuQueue.feed(1);serviceFormatter();assert(workerPending&&sent->count==32&&imuQueue.tail==32);
 complete();assert(!workerPending&&sdRows==32&&bytes.size()==4096);
 imuQueue.feed(3);serviceFormatter();assert(!workerPending);
 recording=false;serviceFormatter();assert(workerPending&&sent->count==3);complete();
 assert(!workerPending&&imuQueue.head==imuQueue.tail&&sdRows==35&&bytes.size()==35*128&&workerErrors==0);
 puts("PASS actual MainCore I/O: 512 offsets, aligned private staging, short writes/EINTR/timeout, full batches, partial STOP drain");
}
'''
path=r/'reports/raw/test_spresense_io.cpp';path.write_text(stub+write_fn+middle+formatter_fn+checks,encoding='utf-8')
exe=path.with_suffix('.exe');zig=Path(ziglang.__file__).parent/('zig.exe' if sys.platform=='win32' else 'zig')
subprocess.run([str(zig),'c++','-std=c++17','-I'+str(r/'common'),'-I'+str(r/'firmware/spresense/libraries/AquaBeacon/src'),str(path),'-o',str(exe)],check=True)
subprocess.run([str(exe)],check=True)
