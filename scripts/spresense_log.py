"""Stream Spresense AQSBIN01 or legacy CRC CSV; export without loading whole files."""
import argparse
import csv
import json
import struct
import zlib
from pathlib import Path

HEADER = struct.Struct('<8sHHBBHIII480sI')
SAMPLE = struct.Struct('<IIQI13fI3Q4IB3sII')
REFERENCE = struct.Struct('<IQ64sB3sQQ4IB11sI')
NAV = struct.Struct('<4s4BIQiii8I')
SAMPLE_KEYS = ('seq received_mono_us sensor_timestamp_raw temp gx gy gz ax ay az '
               'corrected_gx corrected_gy corrected_gz corrected_ax corrected_ay corrected_az '
               'calibration_generation sensor_ticks_unwrapped sample_mono_us sample_utc_us '
               'clock_generation pps_count parent_set_generation parent_session time_quality '
               'time_uncertainty_us').split()
REFERENCE_KEYS = ('seq parent_reference_mono_us utc_s nav_usec flags fix_unused satellites_unused '
                  'lat_unused lon_unused alt_unused imu_samples imu_errors imu_gaps sd_errors sd_rows '
                  'parent_time_source pps_anchor_mono_us pps_anchor_utc_us pps_count pps_period_us '
                  'pps_paired parent_set_generation parent_session').split()


def iter_rows(path, allow_truncated_tail=False, report=None):
    report = report if report is not None else {}
    report.update(rows=0, truncated_tail_bytes=0)
    with Path(path).open('rb') as f:
        prefix = f.read(8)
        f.seek(0)
        if prefix != b'AQSBIN01':
            # Text iteration preserves the old per-row CRC contract, with bounded RAM.
            import io
            text = io.TextIOWrapper(f, encoding='utf-8-sig', newline='')
            keys = next(csv.reader([text.readline().rstrip('\r\n')]))
            if keys not in (SAMPLE_KEYS + ['crc32'], REFERENCE_KEYS + ['crc32']):
                # Earlier IMU schemas are still readable by their column names.
                if (not keys or keys[-1] != 'crc32' or
                        not ('seq' in keys or {'parent_session', 'sample_utc_us', 'time_quality'}.issubset(keys))):
                    raise ValueError('Unknown Spresense log format/header')
            report['format'] = 'CSV'
            for number, line in enumerate(text, 2):
                line = line.rstrip('\r\n')
                body, crc = line.rsplit(',', 1)
                if zlib.crc32(body.encode()) != int(crc, 16):
                    raise ValueError(f'CSV CRC line {number}')
                fields = next(csv.reader([line]))
                if len(fields) != len(keys):
                    raise ValueError(f'CSV column count line {number}')
                report['rows'] += 1
                yield dict(zip(keys, fields))
            return
        raw = f.read(HEADER.size)
        if len(raw) != HEADER.size:
            raise ValueError('Truncated Spresense binary header')
        magic, version, size, stream, flags, record_size, file_id, rate, reserved, padding, crc = HEADER.unpack(raw)
        if (version != 1 or size != 512 or stream not in (1, 2) or flags or record_size != 128
                or reserved or any(padding) or zlib.crc32(raw[:-4]) != crc or rate != 960):
            raise ValueError('Invalid Spresense binary header/version/CRC')
        report.update(format='AQSBIN01', stream=stream, file_id=file_id, rate_hz=rate)
        while True:
            raw = f.read(record_size)
            if not raw:
                return
            if len(raw) != record_size:
                if allow_truncated_tail:
                    report['truncated_tail_bytes'] = len(raw)
                    return
                raise ValueError('Truncated Spresense binary record')
            if zlib.crc32(raw[:-4]) != struct.unpack_from('<I', raw, 124)[0]:
                raise ValueError(f'Spresense binary CRC record {report["rows"] + 1}')
            if stream == 1:
                v = SAMPLE.unpack(raw)
                if v[0] != 0x344d4953 or any(v[-3]) or v[25] not in (0, 1, 2) or v[-2] != 0xffffffff:
                    raise ValueError('Invalid Spresense sample tag/reserved/quality')
                row = dict(zip(SAMPLE_KEYS, v[1:-3] + (v[-2],)))
            else:
                tag, received, nav, source, pad, mono, utc, count, period, setting, parent, paired, pad2, _ = REFERENCE.unpack(raw)
                n = NAV.unpack(nav)
                if (tag != 0x34464552 or any(pad) or any(pad2) or paired > 1 or source > 3
                        or n[0] != b'AQB1' or n[1] != 1 or zlib.crc32(nav[:-4]) != n[-1]):
                    raise ValueError('Invalid Spresense reference/nav')
                values = (n[5], received, n[6], n[10], n[2], n[3], n[4], n[7], n[8], n[9],
                          n[11], n[12], n[16], n[13], n[15], source, mono, utc, count, period, paired, setting, parent)
                row = dict(zip(REFERENCE_KEYS, values))
            report['rows'] += 1
            yield row


def export_csv(source, destination, allow_truncated_tail=False):
    report = {}
    # Exclusive creation protects an existing export and the input log.
    with Path(destination).open('x', encoding='utf-8', newline='') as out:
        writer = csv.writer(out, lineterminator='\n')
        keys = None
        for row in iter_rows(source, allow_truncated_tail, report):
            if keys is None:
                keys = [k for k in row if k != 'crc32']
                writer.writerow(keys + ['crc32'])
            values = [row[k] for k in keys]
            body = ','.join(str(x) for x in values)
            out.write(f'{body},{zlib.crc32(body.encode()):08x}\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source'); parser.add_argument('destination')
    parser.add_argument('--allow-truncated-tail', action='store_true', help='Recover whole records only; report discarded tail bytes')
    args = parser.parse_args()
    print(json.dumps(export_csv(args.source, args.destination, args.allow_truncated_tail), indent=2))
