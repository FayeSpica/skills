#!/usr/bin/env python3
"""
SOR (Standard OTDR Record) File Parser

Wraps the pyotdr library to parse OTDR SOR files (Bellcore SR-4731)
and output key information as JSON or human-readable text summary.

Dependencies:
    pip install pyotdr

Usage:
    python sor_parser.py <file.sor>              # Text summary
    python sor_parser.py <file.sor> --json        # JSON output
    python sor_parser.py <file.sor> --json --pretty  # Pretty-printed JSON
"""

import json
import sys
from pathlib import Path

try:
    from pyotdr import sorparse
except ImportError:
    print("Error: pyotdr is required. Install with: pip install pyotdr", file=sys.stderr)
    sys.exit(1)


# --- Constants ---

FIBER_TYPES = {
    "651": "G.651 (multimode)",
    "652": "G.652 (standard SM)",
    "653": "G.653 (dispersion-shifted)",
    "654": "G.654 (cut-off shifted)",
    "655": "G.655 (NZ-DSF)",
    "656": "G.656 (wideband NZ-DSF)",
    "657": "G.657 (bend-insensitive)",
}

BUILD_CONDITIONS = {
    "BC": "as-built",
    "CC": "as-current",
    "RC": "as-repaired",
    "OT": "other",
}


def parse_sor(filepath: str) -> dict:
    """Parse a SOR file via pyotdr and return a cleaned-up result dict."""
    status, results, tracedata = sorparse(filepath)
    if status != "ok":
        raise RuntimeError(f"pyotdr parse failed: {status}")

    output = {
        "filename": Path(filepath).name,
        "file_size_bytes": Path(filepath).stat().st_size,
    }

    # Block list
    if "blocks" in results:
        output["blocks_found"] = list(results["blocks"].keys())

    # Equipment (SupParams)
    sup = results.get("SupParams", {})
    if sup:
        output["equipment"] = {
            "supplier": sup.get("supplier", ""),
            "otdr_model": sup.get("OTDR", ""),
            "otdr_sn": sup.get("OTDR S/N", ""),
            "module": sup.get("module", ""),
            "module_sn": sup.get("module S/N", ""),
            "software": sup.get("software", ""),
            "other": sup.get("other", ""),
        }

    # General parameters (GenParams)
    gen = results.get("GenParams", {})
    if gen:
        fiber_type_raw = str(gen.get("fiber type", ""))
        output["general"] = {
            "cable_id": gen.get("cable ID", ""),
            "fiber_id": gen.get("fiber ID", ""),
            "fiber_type": fiber_type_raw,
            "fiber_type_name": FIBER_TYPES.get(fiber_type_raw, fiber_type_raw),
            "wavelength_nm": gen.get("wavelength", ""),
            "location_a": gen.get("location A", ""),
            "location_b": gen.get("location B", ""),
            "cable_code": gen.get("cable code", ""),
            "build_condition": gen.get("build condition", ""),
            "build_condition_name": BUILD_CONDITIONS.get(
                str(gen.get("build condition", "")),
                str(gen.get("build condition", "")),
            ),
            "operator": gen.get("operator", ""),
            "comment": gen.get("comment", ""),
        }

    # Fixed/acquisition parameters (FxdParams)
    fxd = results.get("FxdParams", {})
    if fxd:
        output["acquisition"] = {
            "datetime": fxd.get("date/time", ""),
            "units": fxd.get("unit", ""),
            "wavelength_nm": fxd.get("wavelength", ""),
            "pulse_width_ns": fxd.get("pulse width", []),
            "sample_spacing": fxd.get("sample spacing", []),
            "num_data_points": fxd.get("num data points", ""),
            "group_index": fxd.get("index", ""),
            "backscatter_dB": fxd.get("BC", ""),
            "num_averages": fxd.get("num averages", ""),
            "range_km": fxd.get("range", ""),
            "loss_threshold_dB": fxd.get("loss thr", ""),
            "reflectance_threshold_dB": fxd.get("refl thr", ""),
            "eof_threshold_dB": fxd.get("EOT thr", ""),
        }

    # Key events
    kevt = results.get("KeyEvents", {})
    if kevt:
        num_events = kevt.get("num events", 0)
        events = []
        for i in range(1, num_events + 1):
            evt_key = f"event {i}"
            evt = kevt.get(evt_key, {})
            if not evt:
                continue
            events.append({
                "event_number": i,
                "distance_km": evt.get("distance", ""),
                "slope_dBkm": evt.get("slope", ""),
                "splice_loss_dB": evt.get("splice loss", ""),
                "reflectance_dB": evt.get("refl loss", ""),
                "event_type": evt.get("type", ""),
                "comment": evt.get("comment", ""),
            })

        summary = kevt.get("Summary", {})
        output["key_events"] = {
            "num_events": num_events,
            "events": events,
            "total_loss_dB": summary.get("total loss", ""),
            "orl_dB": summary.get("ORL", ""),
            "loss_start": summary.get("loss start", ""),
            "loss_finish": summary.get("loss finish", ""),
        }

    # Trace data summary (count only)
    if tracedata:
        output["trace_data"] = {
            "num_points": len(tracedata),
            "note": "Trace data parsed but not included in output for brevity",
        }

    return output


# --- Output Formatting ---

def print_summary(parsed: dict):
    """Print human-readable summary."""
    print(f"=== SOR File: {parsed['filename']} ({parsed['file_size_bytes']} bytes) ===")
    if "blocks_found" in parsed:
        print(f"Blocks: {', '.join(parsed['blocks_found'])}")
    print()

    # Equipment
    equip = parsed.get("equipment", {})
    if equip:
        print("--- Equipment ---")
        _pf("Supplier", equip.get("supplier"))
        _pf("OTDR Model", equip.get("otdr_model"))
        _pf("OTDR S/N", equip.get("otdr_sn"))
        _pf("Module", equip.get("module"))
        _pf("Module S/N", equip.get("module_sn"))
        _pf("Software", equip.get("software"))
        print()

    # General parameters
    gen = parsed.get("general", {})
    if gen:
        print("--- General Parameters ---")
        _pf("Cable ID", gen.get("cable_id"))
        _pf("Fiber ID", gen.get("fiber_id"))
        _pf("Fiber Type", gen.get("fiber_type_name"))
        _pf("Wavelength", _unit(gen.get("wavelength_nm"), "nm"))
        _pf("Location A", gen.get("location_a"))
        _pf("Location B", gen.get("location_b"))
        _pf("Operator", gen.get("operator"))
        _pf("Build Cond.", gen.get("build_condition_name"))
        _pf("Comment", gen.get("comment"))
        print()

    # Acquisition parameters
    acq = parsed.get("acquisition", {})
    if acq:
        print("--- Acquisition Parameters ---")
        _pf("Date/Time", acq.get("datetime"))
        _pf("Units", acq.get("units"))
        _pf("Wavelength", _unit(acq.get("wavelength_nm"), "nm"))
        _pf("Pulse Width", _unit(acq.get("pulse_width_ns"), "ns"))
        _pf("Group Index", acq.get("group_index"))
        _pf("Backscatter", _unit(acq.get("backscatter_dB"), "dB"))
        _pf("Averages", acq.get("num_averages"))
        _pf("Range", _unit(acq.get("range_km"), "km"))
        _pf("Data Points", acq.get("num_data_points"))
        _pf("Loss Thresh", _unit(acq.get("loss_threshold_dB"), "dB"))
        _pf("Refl Thresh", _unit(acq.get("reflectance_threshold_dB"), "dB"))
        _pf("EOF Thresh", _unit(acq.get("eof_threshold_dB"), "dB"))
        print()

    # Key events
    kevt = parsed.get("key_events", {})
    if kevt:
        num = kevt.get("num_events", 0)
        print(f"--- Key Events ({num}) ---")
        for evt in kevt.get("events", []):
            dist = evt.get("distance_km", "?")
            loss = evt.get("splice_loss_dB", "?")
            refl = evt.get("reflectance_dB", "?")
            etype = evt.get("event_type", "")
            print(f"  #{evt['event_number']:>3d}  dist={dist} km  "
                  f"loss={loss} dB  refl={refl} dB  [{etype}]")
            if evt.get("comment"):
                print(f"        comment: {evt['comment']}")
        if kevt.get("total_loss_dB"):
            print(f"\n  Total Loss:  {kevt['total_loss_dB']} dB")
        if kevt.get("orl_dB"):
            print(f"  ORL:         {kevt['orl_dB']} dB")
        print()

    # Trace data
    td = parsed.get("trace_data", {})
    if td:
        print("--- Trace Data ---")
        _pf("Data Points", td.get("num_points"))
        print()


def _pf(label: str, value):
    """Print field if non-empty."""
    if value is not None and value != "" and value != [] and value != 0:
        print(f"  {label:<15s} {value}")


def _unit(value, unit: str):
    """Format value with unit, return None if empty."""
    if value is not None and value != "" and value != 0:
        return f"{value} {unit}"
    return None


# --- CLI ---

def main():
    if len(sys.argv) < 2:
        print("Usage: python sor_parser.py <file.sor> [--json] [--pretty]")
        print()
        print("Options:")
        print("  --json     Output as JSON")
        print("  --pretty   Pretty-print JSON (implies --json)")
        print()
        print("Requires: pip install pyotdr")
        sys.exit(1)

    filepath = sys.argv[1]
    output_json = "--json" in sys.argv
    pretty = "--pretty" in sys.argv
    if pretty:
        output_json = True

    if not Path(filepath).exists():
        print(f"Error: file not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    try:
        parsed = parse_sor(filepath)
    except Exception as e:
        print(f"Error parsing SOR file: {e}", file=sys.stderr)
        sys.exit(1)

    if output_json:
        indent = 2 if pretty else None
        print(json.dumps(parsed, indent=indent, ensure_ascii=False, default=str))
    else:
        print_summary(parsed)


if __name__ == "__main__":
    main()
