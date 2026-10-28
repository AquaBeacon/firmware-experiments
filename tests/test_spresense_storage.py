"""Compile production open/rotation functions against an in-memory SD, no devices."""
from pathlib import Path
import subprocess,sys,ziglang
r=Path(__file__).resolve().parents[1]
source=(r/'firmware/spresense/logger/logger.ino').read_text(encoding='utf-8')
source=source[source.index('bool openLogs() {'):source.index('void resumeRecording()')]
stub=r'''
#include <map>
#include <string>
#include <vector>
#include <atomic>
#include <cassert>
#include <cstdio>
#include <cerrno>
#include "ImuBatch.h"
constexpr int O_CREAT=1,O_EXCL=2,O_RDWR=4,O_RDONLY=8,O_WRONLY=16,F_OK=0;
namespace sprctl {enum {SD_MOUNT,SD_PROBE_OPEN,SD_NAMES,SD_PROBE_IO,SD_LOG_OPEN,SD_HEADER};}
struct statfs {uint64_t f_bavail=1000000,f_bsize=512;};
bool full=false,permission=false,syncFail=false,mounted=true;
struct {bool begin(){return mounted;}} card;
struct {void kick(){}} Watchdog;
struct {void println(const char*){}} Serial;
std::map<std::string,std::vector<uint8_t>> files;
struct Handle {std::string path;size_t offset=0;};std::map<int,Handle> handles;int nextFd=10;
std::vector<std::string> deleted;
int statfs(const char*,struct statfs* v){v->f_bavail=full?0:1000000;return 0;}
int access(const char* p,int){if(permission){errno=EACCES;return -1;}if(files.count(p))return 0;errno=ENOENT;return -1;}
int open(const char* p,int flags,int=0){
 if((flags&O_EXCL)&&files.count(p)){errno=EEXIST;return -1;}
 if(!(flags&O_CREAT)&&!files.count(p)){errno=ENOENT;return -1;}
 files[p];handles[++nextFd]={p,0};return nextFd;
}
long write(int fd,const void* p,size_t n){auto& h=handles.at(fd);auto& bytes=files.at(h.path);bytes.resize(h.offset+n);memcpy(bytes.data()+h.offset,p,n);h.offset+=n;return n;}
long read(int fd,void* p,size_t n){auto& h=handles.at(fd);auto& bytes=files.at(h.path);n=std::min(n,bytes.size()-h.offset);memcpy(p,bytes.data()+h.offset,n);h.offset+=n;return n;}
int close(int fd){assert(handles.erase(fd)==1);return 0;}
int fsync(int){if(syncFail){errno=EIO;return -1;}return 0;}
int unlink(const char* p){deleted.emplace_back(p);return files.erase(p)?0:-1;}
off_t lseek(int fd,off_t,int){return handles.at(fd).offset;}
bool writeComplete(int fd,const char* p,size_t n){return write(fd,p,n)==long(n);}
bool flushLog(int fd,const char*){return fsync(fd)==0;}
int imuFile=-1,gpsFile=-1;char imuPath[64]{},gpsPath[64]{};uint32_t nextLogId=0;
std::atomic<uint32_t> sdRows{100},sdSyncedRows{90};bool sdReady=true;int failure=-1;
bool openFailed(int stage,int error){failure=stage;errno=error;return false;}
void closeLogsAfterFailure(){if(imuFile>=0)close(imuFile);if(gpsFile>=0)close(gpsFile);imuFile=gpsFile=-1;}
void failSd(const char*,int){sdReady=false;closeLogsAfterFailure();}
'''
checks=r'''
int main(){
 full=true;assert(!openLogs()&&errno==ENOSPC&&files.empty()&&handles.empty());full=false;
 permission=true;assert(!openLogs()&&errno==EACCES&&files.empty());permission=false;
 files["/mnt/sd0/I00000.CSV"]={1,2,3};files["/mnt/sd0/T00001.BIN"]={4,5,6};
 auto originals=files;assert(openLogs()&&nextLogId==3&&std::string(imuPath)=="/mnt/sd0/I00002.BIN");
 for(const auto& p:originals)assert(files.at(p.first)==p.second);
 for(const char* path:{imuPath,gpsPath}){sprbin::Header h;assert(files.at(path).size()==512);memcpy(&h,files.at(path).data(),512);assert(sprbin::valid(h)&&h.fileId==2);}
 assert(deleted.size()==1&&deleted[0]=="/mnt/sd0/V00002.BIN");
 auto old=files;rotateLogsIfNeeded();assert(files==old&&nextLogId==3);
 handles.at(imuFile).offset=sprbin::rotateBytes-4096;rotateLogsIfNeeded();assert(nextLogId==3);
 handles.at(imuFile).offset++;rotateLogsIfNeeded();assert(nextLogId==4&&sdReady&&sdRows==100&&sdSyncedRows==100);
 assert(std::string(imuPath)=="/mnt/sd0/I00003.BIN");for(const auto& p:old)assert(files.at(p.first)==p.second);
 handles.at(gpsFile).offset=sprbin::rotateBytes-128;syncFail=true;rotateLogsIfNeeded();assert(!sdReady&&handles.empty()&&nextLogId==4);
 for(const auto& p:originals)assert(files.at(p.first)==p.second);
 puts("PASS production Spresense storage: ENOSPC/permissions before create, legacy names, CRC headers, no overwrite/delete, both rotation thresholds, sync failure");
}
'''
path=r/'reports/raw/test_spresense_storage.cpp';path.write_text(stub+source+checks,encoding='utf-8')
exe=path.with_suffix('.exe');zig=Path(ziglang.__file__).parent/('zig.exe' if sys.platform=='win32' else 'zig')
subprocess.run([str(zig),'c++','-std=c++17','-I'+str(r/'common'),'-I'+str(r/'firmware/spresense/libraries/AquaBeacon/src'),str(path),'-o',str(exe)],check=True)
subprocess.run([str(exe)],check=True)
