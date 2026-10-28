#pragma once
#include <hardware/spi.h>
#include <atomic>
#include "sd_io_deadline.h"
// External SdFat driver: only core 0 owns SPI1. SPI0/BNO is unchanged.
SdIoDeadline sdIoDeadline;
class BoundedSdSpi:public SdSpiBaseClass {
 uint32_t hz=400000;bool fault=false;
 bool allowed(uint64_t transferEnd){
  auto now=time_us_64();
  if(fault||!sdIoDeadline.allow(now)||now>=transferEnd){fault=true;return false;}return true;
 }
 bool transfer(const uint8_t* tx,uint8_t* rx,size_t n){
  // 512 bytes at initialization speed take 10.24 ms. 20 ms bounds FIFO waits.
  uint64_t until=time_us_64()+20000;
  // Keep the RP SPI FIFO busy instead of waiting for every individual byte.
  // At most eight outstanding bytes also bound RX occupancy if interrupted.
  size_t sent=0,received=0;
  while(received<n){
   if(!allowed(until))return false;
   while(sent<n&&sent-received<8&&spi_is_writable(spi1)){
    spi_get_hw(spi1)->dr=tx?tx[sent]:0xff;++sent;
   }
   while(received<sent&&spi_is_readable(spi1)){
    uint8_t value=uint8_t(spi_get_hw(spi1)->dr);if(rx)rx[received]=value;++received;
   }
  }return true;
 }
public:
 std::atomic<uint32_t> receivedBytes{0},sentBytes{0};
 void begin(SdSpiConfig)override{fault=false;receivedBytes=sentBytes=0;hz=400000;SPI1.begin();}
 void end()override{SPI1.end();}
 void setSckSpeed(uint32_t value)override{hz=value;}
 void activate()override{SPI1.beginTransaction(SPISettings(hz,MSBFIRST,SPI_MODE0));}
 void deactivate()override{SPI1.endTransaction();}
 uint8_t receive()override{uint8_t v=0xff;transfer(nullptr,&v,1);return v;}
 uint8_t receive(uint8_t* dst,size_t n)override{receivedBytes+=n;return transfer(nullptr,dst,n)?0:1;}
 void send(uint8_t v)override{transfer(&v,nullptr,1);}
 void send(const uint8_t* src,size_t n)override{sentBytes+=n;transfer(src,nullptr,n);}
 bool failed()const{return fault;}
} sdSpi;
bool sdInitAllowed(){return sdIoDeadline.allow(time_us_64())&&!sdSpi.failed();}
struct SdMountScope {
 SdMountScope(){sdIoDeadline.start(time_us_64(),4000000);}
 ~SdMountScope(){sdIoDeadline.finish();}
};
