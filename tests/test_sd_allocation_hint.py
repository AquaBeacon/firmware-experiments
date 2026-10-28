"""Compile the actual vendored FAT32 hint method with a read-only FAT fixture."""
from pathlib import Path
import subprocess, sys, ziglang
r=Path(__file__).resolve().parents[1]
source=(r/'lib/SdFat/src/FatLib/FatPartition.cpp').read_text(encoding='utf-8')
method=source[source.index('bool FatPartition::primeAllocationHint('):source.index('//------------------------------------------------------------------------------')]
prefix=r'''
#include <cstdint>
#include <cassert>
#include <cstdio>
struct FatPartition {
 uint32_t m_lastCluster=1000001,m_allocSearchStart=1,usedUntil=900000,calls=0;uint8_t m_fatType=32;bool full=false,error=false;
 uint32_t clusterCount(){return m_lastCluster-1;}
 int8_t fatGet(uint32_t c,uint32_t* v){calls++;if(error)return -1;assert(c>=2&&c<=m_lastCluster);*v=full||c<usedUntil?0xfffffff:0;return 1;}
 bool primeAllocationHint(uint32_t);
};
'''
test=r'''
int main(){
 FatPartition f;assert(f.primeAllocationHint(0));assert(f.m_allocSearchStart+1>=f.usedUntil&&f.calls<=8192);
 f=FatPartition{};f.full=true;assert(!f.primeAllocationHint(0)&&f.calls<=8192&&f.m_allocSearchStart==1);
 f=FatPartition{};f.error=true;assert(!f.primeAllocationHint(0)&&f.calls==1&&f.m_allocSearchStart==1);
 f=FatPartition{};f.m_fatType=16;assert(!f.primeAllocationHint(0)&&!f.calls);
 f=FatPartition{};assert(f.primeAllocationHint(0xffffffff)&&f.m_allocSearchStart<f.m_lastCluster);
 puts("PASS actual FAT allocation hint: occupied prefix, full media, read error, unsupported volume, bounds; read-only probing");
}
'''
p=r/'reports/raw/test_sd_allocation_hint.cpp';p.write_text(prefix+method+test,encoding='utf-8')
zig=Path(ziglang.__file__).parent/('zig.exe' if sys.platform=='win32' else 'zig')
subprocess.run([str(zig),'c++','-std=c++17',str(p),'-o',str(p.with_suffix('.exe'))],check=True)
subprocess.run([str(p.with_suffix('.exe'))],check=True)
