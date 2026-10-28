"""Compile the actual parent start diagnostics; cover each clock and calibration gate."""
from pathlib import Path
import subprocess,sys,ziglang
r=Path(__file__).resolve().parents[1]
s=(r/'include/body_calibration_store.h').read_text()
constants=s[s.index('namespace bodyissue {'):s.index('uint32_t bodyLastIssues=')]
fn=s[s.index('uint32_t bodyStartIssues('):s.index('uint8_t bodyAxesState()')]
stub=r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
namespace aq {constexpr unsigned IMU=4;}
bool active=false,sdHealthy=true,stopped=false,stopRequested=false,dumping=false,runRanging=false,calibrationActive=false,parentCalibrationRestoreError=false,setMatch=true,link=true,axesReady=false;
uint32_t imu=1,magref=1;
void bodyRefs(uint32_t& i,uint32_t& m){i=imu;m=magref;}
bool bodyActive(){return active;}bool bodyExperimentReady(){return axesReady;}
uint64_t time_us_64(){return 100;}
struct Spr {bool recording=true,ppsLocked=true,synchronized=true,imuTimeReady=true;unsigned timeSource=1,calibration=0;}sp;
auto spresenseSnapshot(){return sp;}bool spresenseFresh(Spr,uint64_t){return link;}
struct Utc {unsigned source=1;bool valid=true;uint64_t at(uint64_t){return valid?100:0;}}utc;
auto utcSnapshot(){return utc;}
struct Mag {bool active=false;}mag;
auto i2c_mag_calibration(){return mag;}bool parentCalibrationMatches(){return setMatch;}
'''
checks=r'''
int main(){
 assert(bodyStartIssues()==0);assert(bodyStartIssues(true)==bodyissue::axes);axesReady=true;assert(!bodyStartIssues(true));
 active=true;assert(bodyStartIssues()==bodyissue::active);active=false;
 sdHealthy=false;assert(bodyStartIssues()==bodyissue::sd);sdHealthy=true;
 stopped=true;assert(bodyStartIssues()==bodyissue::record);stopped=false;
 stopRequested=true;assert(bodyStartIssues()==bodyissue::stopping);stopRequested=false;
 dumping=true;assert(bodyStartIssues()==bodyissue::dump);dumping=false;
 runRanging=true;assert(bodyStartIssues()==bodyissue::ranging);runRanging=false;
 calibrationActive=true;assert(bodyStartIssues()==bodyissue::calibration);calibrationActive=false;
 mag.active=true;assert(bodyStartIssues()==bodyissue::calibration);mag.active=false;
 sp.calibration=1;assert(bodyStartIssues()==bodyissue::calibration);sp.calibration=6;assert(bodyStartIssues()==bodyissue::calibration);sp.calibration=0;
 imu=0;assert(bodyStartIssues()==bodyissue::imuCalibration);imu=1;magref=0;assert(bodyStartIssues()==bodyissue::magCalibration);magref=1;
 setMatch=false;assert(bodyStartIssues()==bodyissue::parentSet);setMatch=true;parentCalibrationRestoreError=true;assert(bodyStartIssues()==bodyissue::parentSet);parentCalibrationRestoreError=false;
 link=false;assert(bodyStartIssues()==bodyissue::sprLink);link=true;
 sp.recording=false;assert(bodyStartIssues()==bodyissue::sprRecord);sp.recording=true;
 sp.ppsLocked=false;assert(bodyStartIssues()==bodyissue::sprPps);sp.ppsLocked=true;
 sp.synchronized=false;assert(bodyStartIssues()==bodyissue::sprUtc);sp.synchronized=true;sp.timeSource=3;assert(bodyStartIssues()==bodyissue::sprUtc);sp.timeSource=1;
 sp.imuTimeReady=false;assert(bodyStartIssues()==bodyissue::imuTime);sp.imuTimeReady=true;
 utc.source=3;assert(bodyStartIssues()==bodyissue::parentUtc);utc.source=1;utc.valid=false;assert(bodyStartIssues()==bodyissue::parentUtc);utc.valid=true;
 stopped=true;sp.recording=false;utc.valid=false;assert(bodyStartIssues()==(bodyissue::record|bodyissue::sprRecord|bodyissue::parentUtc));
 puts("PASS production parent readiness: all individual causes, independent clocks, calibration and simultaneous failures");
}
'''
p=r/'reports/raw/test_body_readiness.cpp';p.write_text(stub+constants+fn+checks)
zig=Path(ziglang.__file__).parent/('zig.exe' if sys.platform=='win32' else 'zig')
exe=p.with_suffix('.exe');subprocess.run([str(zig),'c++','-std=c++17','-DBOARD_PARENT',str(p),'-o',str(exe)],check=True)
subprocess.run([str(exe)],check=True)
