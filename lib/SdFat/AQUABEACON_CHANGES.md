# AquaBeacon local SdFat changes

Upstream: SdFat 2.3.1 (MIT), copied from the Arduino-Pico package used by this
project on 2026-10-27. The package and adjacent repositories are unchanged.
Keep LICENSE.md and the upstream source notices. Ancillary upstream files are
retained; the firmware builds only the library sources.

Only FatLib/FatPartition.h/.cpp and FsLib/FsVolume.h have local changes:
`primeAllocationHint(seed)` probes at most 64 windows of 128 FAT32 entries,
checks an entry is actually free, then updates the allocator's in-memory hint.
It never changes a FAT entry or trusts a cached free-space count. Unsupported
filesystems keep their original allocation policy. If no free candidate is
found, normal allocation remains subject to the firmware's initialization
deadline. The normal allocator still verifies and marks every allocated entry.

The firmware uses SdFat's external SPI interface (`SPI_DRIVER_SELECT=3`) with
`include/sd_bounded_spi.h`. No changes to the installed framework are needed.
