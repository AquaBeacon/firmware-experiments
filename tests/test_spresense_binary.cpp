#include "ImuBatch.h"
#include <cassert>
#include <cstdio>
#include <cmath>
int main(int argc,char** argv){
 assert(argc==3);
 aqimu::Batch batch{};batch.version=aqimu::magic;batch.count=aqimu::batchSize;
 for(unsigned i=0;i<batch.count;i++){
  auto& r=batch.rows[i];r.seq=0xfffffff0u+i;r.received_us=0x100000000ULL+i*1042;
  r.data={0xfffffff0u+i,23.25f,-0.0f,0.002f,-0.003f,0.01f,-0.02f,9.80665f};
  const float raw[]={r.data.gx,r.data.gy,r.data.gz,r.data.ax,r.data.ay,r.data.az};
  memcpy(r.corrected,raw,sizeof(raw));r.sensor_ticks=0x200000000ULL+i;r.sample_mono_us=r.received_us-200;
  r.sample_utc_us=1793055600000000ULL+i*1042;r.clock_generation=7;r.pps_count=11;r.set_generation=3;r.parent_session=999;r.time_quality=2;
 }
 assert(aqimu::formatBinary(batch)&&batch.length==4096&&batch.error==0);
 sprbin::Header h;h.stream=1;h.fileId=123;sprbin::seal(h);assert(sprbin::valid(h));
 FILE* f=fopen(argv[1],"wb");assert(f);assert(fwrite(&h,1,sizeof(h),f)==sizeof(h));assert(fwrite(batch.csv,1,batch.length,f)==batch.length);assert(!fclose(f));
 for(unsigned i=0;i<batch.count;i++){
  sprbin::Sample s;memcpy(&s,batch.csv+i*sizeof(s),sizeof(s));
  assert(sprbin::valid(s)&&s.seq==batch.rows[i].seq&&s.received==batch.rows[i].received_us);
  assert(s.quality==2&&s.uncertainty==UINT32_MAX&&s.calibration==0&&s.parent==999);
  assert(std::signbit(s.values[1]));
  for(unsigned j=0;j<sizeof(s);j++){auto p=reinterpret_cast<uint8_t*>(&s);p[j]^=1;assert(!sprbin::valid(s));p[j]^=1;}
 }
 batch.count=0;assert(!aqimu::formatBinary(batch));batch.count=33;assert(!aqimu::formatBinary(batch));
 batch.count=1;batch.version=0x494d5533;assert(!aqimu::formatBinary(batch));
 sprbin::Reference ref;ref.received=0x100000001ULL;ref.source=1;ref.ppsMono=0x100000002ULL;ref.ppsUtc=1793055600000000ULL;
 ref.ppsCount=19;ref.ppsPeriod=1000000;ref.set=3;ref.parent=999;ref.paired=1;
 aq::Nav nav;nav.sequence=42;nav.utc_s=1793055600;nav.flags=1;nav.usec=321;nav.imu_samples=987;nav.imu_errors=2;nav.imu_gaps=7;nav.sd_errors=8;nav.sd_rows=901;aq::encode(nav,ref.nav);sprbin::seal(ref);
 h.stream=2;sprbin::seal(h);f=fopen(argv[2],"wb");assert(f);assert(fwrite(&h,1,sizeof(h),f)==sizeof(h));assert(fwrite(&ref,1,sizeof(ref),f)==sizeof(ref));assert(!fclose(f));
 assert(!sprbin::mustRotate(sprbin::rotateBytes-4096,4096));assert(sprbin::mustRotate(sprbin::rotateBytes-4095,4096));
 assert(sprbin::mustRotate(UINT32_MAX,128));assert(sprbin::mustRotate(0,size_t(sprbin::rotateBytes)+1));
 puts("PASS Spresense binary: packed ABI, all sample bits/CRC, 64-bit time, sequence wrap, core version, reference, rotation bounds");
}
