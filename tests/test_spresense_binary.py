from pathlib import Path
import sys,struct,tempfile,zlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from spresense_log import iter_rows,export_csv,SAMPLE,REFERENCE,HEADER
from verify_spresense_log import verify
source,reference=map(Path,sys.argv[1:])
rows=list(iter_rows(source));refs=list(iter_rows(reference))
assert len(rows)==32 and rows[0]['seq']==0xfffffff0 and rows[-1]['seq']==15
assert rows[0]['received_mono_us']==0x100000000 and rows[0]['parent_session']==999
assert refs[0]['imu_gaps']==7 and refs[0]['sd_rows']==901 and refs[0]['parent_time_source']==1
assert refs[0]['parent_reference_mono_us']==0x100000001 and refs[0]['pps_anchor_mono_us']==0x100000002
assert refs[0]['seq']==42 and refs[0]['nav_usec']==321 and refs[0]['pps_paired']==1
assert verify(source)['sequence_gaps']==0
with tempfile.TemporaryDirectory() as folder:
 p=Path(folder)/'log.bin';csv=Path(folder)/'samples.csv'
 assert export_csv(source,csv)['rows']==32
 assert verify(csv)['rows']==32
 try:export_csv(source,csv);raise AssertionError('Overwrote CSV')
 except FileExistsError:pass
 data=source.read_bytes()
 for length in (1,31,511,513,len(data)-1):
  p.write_bytes(data[:length])
  try:list(iter_rows(p));raise AssertionError('Accepted truncated data')
  except (ValueError,UnicodeError):pass
 p.write_bytes(data[:-1]);report={};assert len(list(iter_rows(p,True,report)))==31 and report['truncated_tail_bytes']==127
 # Every disk byte belongs to a checked header/record CRC, including padding.
 for i in range(len(data)):
  bad=bytearray(data);bad[i]^=1;p.write_bytes(bad)
  try:list(iter_rows(p));raise AssertionError(f'Corruption accepted at {i}')
  except (ValueError,UnicodeError):pass
 # Valid outer CRC with wrong tag/version/stream/reserved is also rejected.
 for i in (8,12,13,14,24,512,512+121):
  bad=bytearray(data);bad[i]^=1;end=512 if i<512 else 640;begin=0 if i<512 else 512
  struct.pack_into('<I',bad,end-4,zlib.crc32(bad[begin:end-4]));p.write_bytes(bad)
  try:list(iter_rows(p));raise AssertionError(f'Bad ABI accepted at {i}')
  except ValueError:pass
 # Legacy CSV schema 3 remains readable and is verified by the same entry point.
 legacy=Path(__file__).resolve().parents[1]/'reports/raw/spresense_schema3_fixture.csv'
 assert verify(legacy)['rows']==1
print('PASS streaming binary/CSV reader: cross-language fields, CRC corruption, strict truncation, explicit tail salvage, CSV export, legacy input')
