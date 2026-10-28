#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstddef>
#include <atomic>
#include <deque>
#include <vector>
uint64_t fakeNow=1;uint64_t time_us_64(){return fakeNow+=100;}
struct SdSpiConfig{};
struct SdSpiBaseClass{virtual void begin(SdSpiConfig)=0;virtual void end(){};virtual void setSckSpeed(uint32_t){};virtual void activate(){};virtual void deactivate(){};virtual uint8_t receive()=0;virtual uint8_t receive(uint8_t*,size_t)=0;virtual void send(uint8_t)=0;virtual void send(const uint8_t*,size_t)=0;};
struct SPISettings{SPISettings(uint32_t,int,int){}};constexpr int MSBFIRST=1,SPI_MODE0=0;
void resetSpi();
struct {void begin(){resetSpi();}void end(){}void beginTransaction(SPISettings){}void endTransaction(){}}SPI1;
bool writable=true,readable=true;
std::deque<uint8_t> fifo;std::vector<uint8_t> transmitted;size_t peak=0;
struct Register {
 void operator=(uint32_t v){assert(fifo.size()<8);fifo.push_back(uint8_t(v));transmitted.push_back(uint8_t(v));if(fifo.size()>peak)peak=fifo.size();}
 operator uint32_t(){assert(!fifo.empty());auto v=fifo.front();fifo.pop_front();return v;}
};
struct FakeHw{Register dr;}hw;
void resetSpi(){fifo.clear();transmitted.clear();peak=0;}
constexpr int spi1=1;bool spi_is_writable(int){return writable&&fifo.size()<8;}bool spi_is_readable(int){return readable&&!fifo.empty();}FakeHw* spi_get_hw(int){return &hw;}
#include "sd_bounded_spi.h"
int main(){
 SdIoDeadline d;d.start(100,1000);assert(d.allow(1099)&&!d.allow(1100));d.finish();assert(!d.allow(1101));d.start(2000,10);assert(d.allow(2001));assert(!d.allow(1999));
 sdSpi.begin({});uint8_t data[4];assert(sdSpi.receive(data,4)==0&&!sdSpi.failed());
 assert(transmitted.size()==4&&fifo.empty());for(auto v:data)assert(v==255);
 uint8_t sector[512];sdSpi.begin({});assert(!sdSpi.receive(sector,512));assert(peak==8&&fifo.empty()&&transmitted.size()==512);
 for(unsigned i=0;i<512;i++)sector[i]=uint8_t(i);
 sdSpi.begin({});sdSpi.send(sector,512);assert(!sdSpi.failed()&&fifo.empty()&&peak==8);for(unsigned i=0;i<512;i++)assert(transmitted[i]==uint8_t(i));
 sdSpi.begin({});sdSpi.send(uint8_t(0x35));assert(sdSpi.receive()==255&&fifo.empty()&&transmitted[0]==0x35);
 writable=false;auto start=fakeNow;assert(sdSpi.receive(data,4)!=0&&sdSpi.failed());assert(fakeNow-start<=20500);
 writable=true;sdSpi.begin({});readable=false;start=fakeNow;assert(sdSpi.receive(data,4)!=0&&sdSpi.failed());assert(fakeNow-start<=20500);
 readable=true;sdSpi.begin({});sdIoDeadline.start(fakeNow,150);assert(sdSpi.receive(data,4)!=0&&sdIoDeadline.expired);sdIoDeadline.finish();
 sdSpi.begin({});sdIoDeadline.start(fakeNow,100000);assert(sdSpi.receive(data,4)==0);sdIoDeadline.finish();
 assert(sdLogNumber(76,0)==76&&sdLogNumber(99999,1)==0);assert(sdLogNumber(0xffffffff,31)<100000);
 puts("PASS actual bounded SD SPI: TX/RX stalls, cumulative deadline, sticky failure, clean retry and bounded names");
}
