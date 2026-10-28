#pragma once
#include <stddef.h>
#include <stdint.h>
#include <string.h>
// Aggregate each stream separately to avoid evicting SdFat's shared sector cache
// for every short record. The byte stream, including split records, is unchanged.
template<size_t N> class SectorLogBuffer {
 static_assert(N>=512&&N%512==0,"Whole SD sectors required");
 uint8_t data[N];size_t used=0,offset=0;bool failed=false;
public:
 void reset(size_t fileOffset){used=0;offset=fileOffset%512;failed=false;}
 template<class Sink> bool flush(Sink sink){
  if(failed)return false;
  if(!used)return true;
  if(!sink(data,used)){failed=true;return false;}
  offset=(offset+used)%512;used=0;return true;
 }
 template<class Sink> bool append(const uint8_t* src,size_t n,Sink sink){
  if(failed)return false;
  while(n){
   size_t target=N-offset,part=target-used;if(part>n)part=n;
   memcpy(data+used,src,part);used+=part;src+=part;n-=part;
   if(used==target&&!flush(sink))return false;
  }return true;
 }
 size_t pending()const{return used;}
};
