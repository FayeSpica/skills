# SOR File Format Reference

Binary format defined by Bellcore SR-4731 / Telcordia GR-196 for OTDR measurement data.

## Encoding

- All integers: little-endian
- Strings: null-terminated, Latin-1 encoded
- Float values: stored as scaled integers (e.g., dB x 1000)

## Block Structure

Files are organized as sequential blocks. The first block is always Map, which indexes all other blocks.

| Block | Content |
|-------|---------|
| Map | Directory of all blocks (name, version, size) |
| GenParams | Cable/fiber ID, fiber type, wavelength, locations |
| SupParams | Equipment manufacturer, model, serial numbers |
| FxdParams | Acquisition date/time, pulse width, range, thresholds |
| DataPts | Raw OTDR trace data points |
| KeyEvents | Detected events (splices, connectors, bends, end-of-fiber) |
| Cksum | CRC-16 checksum |

## Key Data Conversions

| Raw Field | Unit | Conversion |
|-----------|------|------------|
| wavelength (uint16) | nm | direct or ÷10 depending on block |
| time values (uint32) | 100 ps | × 1e-10 for seconds |
| group_index (uint32) | — | ÷ 100000 |
| backscatter (uint16) | dB | × -0.1 |
| loss/threshold (uint16) | dB | ÷ 1000 |
| reflectance (int16/int32) | dB | ÷ 1000 (negative) |
| distance from time | m | time_s × c / (2 × group_index) |

## Fiber Type Codes

| Code | Standard |
|------|----------|
| 651 | G.651 (multimode) |
| 652 | G.652 (standard single-mode) |
| 653 | G.653 (dispersion-shifted) |
| 654 | G.654 (cut-off shifted) |
| 655 | G.655 (NZ-DSF) |
| 656 | G.656 (wideband NZ-DSF) |
| 657 | G.657 (bend-insensitive) |

## Event Type String

Event type is encoded as a short string (commonly 8 chars). Key positions:

- Char 0: reflection — `0`=non-reflective, `1`=reflective, `2`=saturated
- Char 1: origin — `F`=end-of-fiber, `A`=user-added, `O`=OTDR-found, `M`=user-moved
- Char 6: fiber marker — `L`=launch fiber, `T`=tail fiber

## Version Differences

- **v1.x** (version < 200): Fewer fields in GenParams/FxdParams, smaller KeyEvents structure (22 bytes per event without segment positions).
- **v2.x** (version >= 200): Additional distance fields, trace type in FxdParams, segment position data in KeyEvents.
