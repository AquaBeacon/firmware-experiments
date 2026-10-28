#pragma once
#include <stdint.h>
// One cumulative initialization budget; a failed attempt must unwind, never extend it.
struct SdIoDeadline {
 bool armed=false,expired=false;uint64_t began=0,limit=0;
 void start(uint64_t now,uint64_t budget){armed=true;expired=false;began=now;limit=budget;}
 bool allow(uint64_t now){if(armed&&(now<began||now-began>=limit))expired=true;return !expired;}
 void finish(){armed=false;}
};
// Session-random starting point avoids rescanning every existing numbered log.
inline uint32_t sdLogNumber(uint32_t session,unsigned attempt){return (session%100000+attempt)%100000;}
