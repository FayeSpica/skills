---
name: sor-parser
description: Parse and analyze OTDR SOR files (Bellcore SR-4731 / Telcordia GR-196 binary format) used in fiber optic testing. Use when the user provides a .sor file, asks to read/analyze OTDR measurement data, extract fiber optic test results, or inspect key events (splices, connectors, bends, end-of-fiber), total loss, ORL, equipment info, or acquisition parameters from an OTDR trace file.
---

# SOR Parser

Parse OTDR SOR binary files to extract key fiber optic measurement information: equipment, fiber identification, acquisition parameters, and key events (splices, connectors, reflective/non-reflective events).

## Quick Start

Run the bundled parser script on any `.sor` file:

```bash
# Human-readable summary
python scripts/sor_parser.py <file.sor>

# Structured JSON
python scripts/sor_parser.py <file.sor> --json

# Pretty-printed JSON
python scripts/sor_parser.py <file.sor> --json --pretty
```

No external dependencies required — uses only Python standard library (`struct`, `json`, `datetime`).

## What Gets Extracted

The parser extracts these key fields from the SOR binary:

1. **Equipment** — OTDR supplier, model, serial number, optical module, software version
2. **General Parameters** — cable/fiber ID, fiber type (G.652 etc.), wavelength, locations A/B, operator, build condition
3. **Acquisition Parameters** — date/time, pulse width, group index, backscatter coefficient, range, averaging, loss/reflectance/EOF thresholds
4. **Key Events** — each splice/connector/bend with distance (m), splice loss (dB), reflectance (dB), event type description
5. **Summary** — total loss, optical return loss (ORL), fiber length

Raw trace data points (DataPts block) are summarized by count only to keep output concise.

## Interpreting Results

- **Splice loss**: typical good fusion splice < 0.1 dB; mechanical splice < 0.5 dB
- **Reflectance**: connectors typically -35 to -55 dB; fusion splices typically < -60 dB (non-reflective)
- **Event type codes**: `0`=non-reflective, `1`=reflective, `F`=end-of-fiber, `L`=launch fiber, `T`=tail fiber
- **Distance**: calculated from time-of-travel using `distance = time × c / (2 × group_index)`

## Format Details

For SOR binary format specifications (block structures, data types, version differences), see [references/sor_format.md](references/sor_format.md).
