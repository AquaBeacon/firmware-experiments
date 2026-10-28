#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <limits>
namespace sprbin {
// Explicit packed disk layout; never write the padded acquisition Row ABI.
constexpr uint32_t sampleMagic=0x344d4953; // SIM4
constexpr uint32_t referenceMagic=0x34464552; // REF4
constexpr size_t headerBytes=512,recordBytes=128;
constexpr uint32_t rotateBytes=256u*1024u*1024u; // Below signed 32-bit off_t.
inline uint32_t crc32(const void* data,size_t n){
 auto p=static_cast<const uint8_t*>(data);uint32_t c=~0u;
 while(n--){c^=*p++;for(unsigned i=0;i<8;++i)c=(c>>1)^(0xedb88320u&(0u-(c&1)));}return ~c;
}
#pragma pack(push,1)
struct Header {
 char magic[8]={'A','Q','S','B','I','N','0','1'};
 uint16_t version=1,bytes=headerBytes;
 uint8_t stream=0,flags=0;
 uint16_t recordSize=recordBytes;
 uint32_t fileId=0,rate=960,reserved=0;
 uint8_t padding[480]{};
 uint32_t crc=0;
};
struct Sample {
 uint32_t magic=sampleMagic,seq=0;
 uint64_t received=0;
 uint32_t rawTimestamp=0;
 float values[13]{};
 uint32_t calibration=0;
 uint64_t ticks=0,mono=0,utc=0;
 uint32_t clock=0,pps=0,set=0,parent=0;
 uint8_t quality=0,reserved[3]{};
 uint32_t uncertainty=UINT32_MAX,crc=0;
};
struct Reference {
 uint32_t magic=referenceMagic;
 uint64_t received=0;
 uint8_t nav[64]{},source=0,reserved[3]{};
 uint64_t ppsMono=0,ppsUtc=0;
 uint32_t ppsCount=0,ppsPeriod=0,set=0,parent=0;
 uint8_t paired=0,padding[11]{};
 uint32_t crc=0;
};
#pragma pack(pop)
static_assert(sizeof(Header)==headerBytes && sizeof(Sample)==recordBytes && sizeof(Reference)==recordBytes,"Spresense binary disk ABI");
static_assert(sizeof(float)==4 && std::numeric_limits<float>::is_iec559,"IEEE754 required");
template<class T> inline void seal(T& r){r.crc=crc32(&r,sizeof(r)-4);}
template<class T> inline bool valid(const T& r){return r.crc==crc32(&r,sizeof(r)-4);}
template<class Row> inline Sample sample(const Row& r){
 Sample s;s.seq=r.seq;s.received=r.received_us;s.rawTimestamp=r.data.timestamp;
 const float values[]={r.data.temp,r.data.gx,r.data.gy,r.data.gz,r.data.ax,r.data.ay,r.data.az};
 memcpy(s.values,values,sizeof(values));memcpy(s.values+7,r.corrected,sizeof(r.corrected));
 s.calibration=r.calibration;s.ticks=r.sensor_ticks;s.mono=r.sample_mono_us;s.utc=r.sample_utc_us;
 s.clock=r.clock_generation;s.pps=r.pps_count;s.set=r.set_generation;s.parent=r.parent_session;s.quality=r.time_quality;
 seal(s);return s;
}
inline bool mustRotate(uint32_t position,size_t incoming){return incoming>rotateBytes || position>rotateBytes-incoming;}
}
