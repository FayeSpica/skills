#!/usr/bin/env python3
"""
SOR (Standard OTDR Record) File Parser

Parses binary SOR files (Bellcore SR-4731 / Telcordia GR-196) from OTDR instruments.
Extracts key information and outputs JSON or human-readable text summary.

Usage:
    python sor_parser.py <file.sor>              # Text summary
    python sor_parser.py <file.sor> --json        # JSON output
    python sor_parser.py <file.sor> --json --pretty  # Pretty-printed JSON
"""

import struct
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


# --- Constants ---

FIBER_TYPES = {
    651: "G.651 (multimode)",
    652: "G.652 (standard SM)",
    653: "G.653 (dispersion-shifted)",
    654: "G.654 (cut-off shifted)",
    655: "G.655 (NZ-DSF)",
    656: "G.656 (wideband NZ-DSF)",
    657: "G.657 (bend-insensitive)",
}

BUILD_CONDITIONS = {
    "BC": "as-built",
    "CC": "as-current",
    "RC": "as-repaired",
    "OT": "other",
}

TRACE_TYPES = {
    "ST": "standard",
    "RT": "reverse",
    "DT": "difference",
    "RF": "reference",
}


# --- Binary Reader ---

class SORReader:
    """Low-level binary reader with little-endian integer and null-terminated string support."""

    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def read_uint16(self) -> int:
        val = struct.unpack_from("<H", self.data, self.pos)[0]
        self.pos += 2
        return val

    def read_uint32(self) -> int:
        val = struct.unpack_from("<I", self.data, self.pos)[0]
        self.pos += 4
        return val

    def read_int16(self) -> int:
        val = struct.unpack_from("<h", self.data, self.pos)[0]
        self.pos += 2
        return val

    def read_int32(self) -> int:
        val = struct.unpack_from("<i", self.data, self.pos)[0]
        self.pos += 4
        return val

    def read_string(self) -> str:
        try:
            end = self.data.index(b"\x00", self.pos)
        except ValueError:
            end = len(self.data)
        s = self.data[self.pos:end].decode("latin-1")
        self.pos = end + 1
        return s

    def read_bytes(self, n: int) -> bytes:
        val = self.data[self.pos:self.pos + n]
        self.pos += n
        return val

    def seek(self, pos: int):
        self.pos = pos

    def remaining(self, limit: int) -> int:
        return limit - self.pos


# --- Block Parsers ---

def parse_map(reader: SORReader) -> list:
    """Parse Map block. Returns list of {name, version, size} dicts for all blocks."""
    start = reader.pos
    version = reader.read_uint16()
    nbytes = reader.read_uint32()

    # v1 has explicit block count; v2 reads until nbytes consumed
    if version < 200:
        num_blocks = reader.read_uint16()

    blocks = []
    while reader.pos < start + nbytes:
        name = reader.read_string()
        ver = reader.read_uint16()
        size = reader.read_uint32()
        blocks.append({"name": name, "version": ver, "size": size})

    return blocks


def parse_gen_params(reader: SORReader, version: int, block_end: int) -> dict:
    """Parse GenParams block — cable/fiber identification and test setup."""
    result = {}

    result["language_code"] = reader.read_string()
    result["cable_id"] = reader.read_string()
    result["fiber_id"] = reader.read_string()

    fiber_type = reader.read_uint16()
    result["fiber_type"] = fiber_type
    result["fiber_type_name"] = FIBER_TYPES.get(fiber_type, f"unknown ({fiber_type})")

    wavelength = reader.read_uint16()
    result["wavelength_nm"] = wavelength

    result["location_a"] = reader.read_string()
    result["location_b"] = reader.read_string()
    result["cable_code"] = reader.read_string()

    build_cond = reader.read_string()
    result["build_condition"] = build_cond
    result["build_condition_name"] = BUILD_CONDITIONS.get(build_cond, build_cond)

    # user offset (time) — 100 ps units
    result["user_offset_100ps"] = reader.read_int32()

    if version >= 200:
        result["user_offset_distance_01m"] = reader.read_int32()

    result["operator"] = reader.read_string()
    result["comment"] = reader.read_string()

    return result


def parse_fixed_params(reader: SORReader, version: int, block_end: int) -> dict:
    """Parse FxdParams / FixedParams block — acquisition parameters."""
    result = {}

    timestamp = reader.read_uint32()
    result["timestamp"] = timestamp
    if timestamp > 0:
        try:
            result["datetime"] = datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
        except (OSError, ValueError):
            result["datetime"] = None

    result["units_of_distance"] = reader.read_string()

    actual_wavelength = reader.read_uint16()
    result["actual_wavelength_nm"] = actual_wavelength

    result["acquisition_offset_100ps"] = reader.read_int32()

    if version >= 200:
        result["acquisition_offset_distance_01m"] = reader.read_int32()

    num_pulse_widths = reader.read_uint16()
    result["num_pulse_widths"] = num_pulse_widths

    pulse_widths = [reader.read_uint16() for _ in range(num_pulse_widths)]
    result["pulse_widths_ns"] = pulse_widths

    data_spacing = [reader.read_uint32() for _ in range(num_pulse_widths)]
    result["data_spacing_100ps"] = data_spacing

    num_data_points = [reader.read_uint32() for _ in range(num_pulse_widths)]
    result["num_data_points"] = num_data_points

    group_index_raw = reader.read_uint32()
    result["group_index"] = group_index_raw / 100000.0

    backscatter = reader.read_uint16()
    result["backscatter_coefficient_dB"] = -(backscatter / 10.0)

    result["number_of_averages"] = reader.read_uint32()

    avg_time = reader.read_uint16()
    result["averaging_time_s"] = avg_time

    range_val = reader.read_uint32()
    result["range_100ps"] = range_val
    # Convert range to km: range * 1e-6 (approximately)
    result["range_km"] = range_val * 1e-6 if range_val else None

    if version >= 200:
        result["acquisition_range_distance_01m"] = reader.read_int32()

    result["front_panel_offset_100ps"] = reader.read_int32()

    result["noise_floor_level"] = reader.read_uint16()
    result["noise_floor_scale_factor"] = reader.read_uint16()
    result["power_offset_first_point"] = reader.read_uint16()

    loss_thr = reader.read_uint16()
    result["loss_threshold_dB"] = loss_thr / 1000.0

    refl_thr = reader.read_uint16()
    result["reflectance_threshold_dB"] = -(refl_thr / 1000.0)

    eof_thr = reader.read_uint16()
    result["end_of_fiber_threshold_dB"] = eof_thr / 1000.0

    # Trace type (2 chars, v2 only)
    if version >= 200 and reader.pos + 2 <= block_end:
        trace_type_raw = reader.read_bytes(2).decode("latin-1", errors="replace")
        result["trace_type"] = trace_type_raw
        result["trace_type_name"] = TRACE_TYPES.get(trace_type_raw, trace_type_raw)

    return result


def parse_sup_params(reader: SORReader, version: int, block_end: int) -> dict:
    """Parse SupParams block — equipment identification."""
    result = {}
    result["supplier_name"] = reader.read_string()
    result["otdr_mainframe_id"] = reader.read_string()
    result["otdr_mainframe_sn"] = reader.read_string()
    result["optical_module_id"] = reader.read_string()
    result["optical_module_sn"] = reader.read_string()
    result["software_revision"] = reader.read_string()
    result["other"] = reader.read_string()
    return result


def parse_key_events(reader: SORReader, version: int, block_end: int, group_index: float) -> dict:
    """Parse KeyEvents block — splices, connectors, bends, and end-of-fiber."""
    result = {}

    num_events = reader.read_uint16()
    result["num_events"] = num_events

    events = []
    for _ in range(num_events):
        event = {}
        event["event_number"] = reader.read_uint16()

        time_of_travel = reader.read_uint32()
        event["time_of_travel_100ps"] = time_of_travel
        event["distance_m"] = _time_to_distance(time_of_travel, group_index)

        slope = reader.read_int16()
        event["slope_dBkm"] = slope / 1000.0

        splice_loss = reader.read_int16()
        event["splice_loss_dB"] = splice_loss / 1000.0

        reflection = reader.read_int32()
        event["reflectance_dB"] = reflection / 1000.0

        event_type = reader.read_string()
        event["event_type"] = event_type
        event["event_type_description"] = _describe_event_type(event_type)

        if version >= 200:
            event["end_of_previous_event"] = reader.read_uint32()
            event["start_of_current_event"] = reader.read_uint32()
            event["end_of_current_event"] = reader.read_uint32()
            event["start_of_next_event"] = reader.read_uint32()
            event["peak_of_current_event"] = reader.read_uint32()

        event["comment"] = reader.read_string()
        events.append(event)

    result["events"] = events

    # Summary fields after all events
    if reader.pos + 4 <= block_end:
        try:
            total_loss = reader.read_uint32()
            result["total_loss_dB"] = total_loss / 1000.0

            result["fiber_start_position"] = reader.read_int32()

            fiber_length = reader.read_uint32()
            result["fiber_length_100ps"] = fiber_length
            result["fiber_length_m"] = _time_to_distance(fiber_length, group_index)

            if version >= 200 and reader.pos + 4 <= block_end:
                result["fiber_length_01m"] = reader.read_int32()

            if reader.pos + 2 <= block_end:
                orl = reader.read_uint16()
                result["optical_return_loss_dB"] = orl / 1000.0
        except (struct.error, IndexError):
            pass

    return result


def parse_data_pts_summary(reader: SORReader, version: int, block_end: int) -> dict:
    """Parse DataPts block — only extract metadata, skip raw trace data."""
    result = {}

    num_points = reader.read_uint32()
    result["num_data_points"] = num_points

    num_traces = reader.read_uint16()
    result["num_traces"] = num_traces

    # Skip actual trace data (can be very large)
    result["note"] = "Trace data available but not extracted (use --with-trace for full data)"
    return result


# --- Helpers ---

def _time_to_distance(time_100ps: int, group_index: float) -> float:
    """Convert time-of-travel (100 ps units) to one-way distance in meters."""
    if group_index <= 0:
        group_index = 1.46850
    c = 299792458.0  # speed of light m/s
    time_s = time_100ps * 1e-10
    distance = time_s * c / (2.0 * group_index)
    return round(distance, 3)


def _describe_event_type(event_type: str) -> str:
    """Interpret event type code string. Format varies but common patterns exist."""
    if not event_type or len(event_type) < 2:
        return "unknown"
    descriptions = []
    # First char: event origination
    first = event_type[0] if len(event_type) > 0 else ""
    if first == "0":
        descriptions.append("non-reflective")
    elif first == "1":
        descriptions.append("reflective")
    elif first == "2":
        descriptions.append("saturated reflective")
    # Second char: landmark type
    second = event_type[1] if len(event_type) > 1 else ""
    if second == "F":
        descriptions.append("end-of-fiber")
    elif second == "A":
        descriptions.append("added-by-user")
    elif second == "O":
        descriptions.append("found-by-OTDR")
    elif second == "M":
        descriptions.append("moved-by-user")
    # Check for launch/tail fiber flags
    if len(event_type) > 6:
        if event_type[6] == "L":
            descriptions.append("launch-fiber")
        elif event_type[6] == "T":
            descriptions.append("tail-fiber")
    return ", ".join(descriptions) if descriptions else event_type


# --- Main Parse Function ---

def parse_sor(filepath: str) -> dict:
    """Parse a SOR file and return structured dict with key information."""
    data = Path(filepath).read_bytes()
    reader = SORReader(data)

    # Step 1: parse map to discover all blocks
    blocks_info = parse_map(reader)

    # Calculate byte offsets for each block
    offset = 0
    for binfo in blocks_info:
        binfo["offset"] = offset
        offset += binfo["size"]

    result = {
        "filename": str(Path(filepath).name),
        "file_size_bytes": len(data),
        "blocks_found": [b["name"] for b in blocks_info],
    }

    # Build quick lookup
    block_map = {}
    for binfo in blocks_info:
        block_map[binfo["name"]] = binfo

    # Step 2: parse SupParams first (equipment info)
    if "SupParams" in block_map:
        binfo = block_map["SupParams"]
        reader.seek(binfo["offset"])
        try:
            result["equipment"] = parse_sup_params(reader, binfo["version"], binfo["offset"] + binfo["size"])
        except Exception as e:
            result["equipment"] = {"error": str(e)}

    # Step 3: parse GenParams (fiber/cable info)
    if "GenParams" in block_map:
        binfo = block_map["GenParams"]
        reader.seek(binfo["offset"])
        try:
            result["general"] = parse_gen_params(reader, binfo["version"], binfo["offset"] + binfo["size"])
        except Exception as e:
            result["general"] = {"error": str(e)}

    # Step 4: parse FixedParams (acquisition parameters)
    if "FxdParams" in block_map:
        binfo = block_map["FxdParams"]
        reader.seek(binfo["offset"])
        try:
            result["acquisition"] = parse_fixed_params(reader, binfo["version"], binfo["offset"] + binfo["size"])
        except Exception as e:
            result["acquisition"] = {"error": str(e)}

    # Determine group index for distance calculations
    group_index = 1.46850  # default
    if "acquisition" in result and isinstance(result["acquisition"], dict):
        gi = result["acquisition"].get("group_index")
        if gi and gi > 0:
            group_index = gi

    # Step 5: parse KeyEvents
    if "KeyEvents" in block_map:
        binfo = block_map["KeyEvents"]
        reader.seek(binfo["offset"])
        try:
            result["key_events"] = parse_key_events(reader, binfo["version"], binfo["offset"] + binfo["size"], group_index)
        except Exception as e:
            result["key_events"] = {"error": str(e)}

    # Step 6: parse DataPts summary (metadata only, skip raw data)
    if "DataPts" in block_map:
        binfo = block_map["DataPts"]
        reader.seek(binfo["offset"])
        try:
            result["data_points"] = parse_data_pts_summary(reader, binfo["version"], binfo["offset"] + binfo["size"])
        except Exception as e:
            result["data_points"] = {"error": str(e)}

    return result


# --- Output Formatting ---

def print_summary(parsed: dict):
    """Print human-readable summary of parsed SOR file."""
    print(f"=== SOR File: {parsed['filename']} ({parsed['file_size_bytes']} bytes) ===")
    print(f"Blocks: {', '.join(parsed['blocks_found'])}")
    print()

    # Equipment
    equip = parsed.get("equipment", {})
    if equip and "error" not in equip:
        print("--- Equipment ---")
        _print_field("Supplier", equip.get("supplier_name"))
        _print_field("OTDR Model", equip.get("otdr_mainframe_id"))
        _print_field("OTDR S/N", equip.get("otdr_mainframe_sn"))
        _print_field("Module", equip.get("optical_module_id"))
        _print_field("Module S/N", equip.get("optical_module_sn"))
        _print_field("Software", equip.get("software_revision"))
        print()

    # General parameters
    gen = parsed.get("general", {})
    if gen and "error" not in gen:
        print("--- General Parameters ---")
        _print_field("Cable ID", gen.get("cable_id"))
        _print_field("Fiber ID", gen.get("fiber_id"))
        _print_field("Fiber Type", gen.get("fiber_type_name"))
        _print_field("Wavelength", f"{gen['wavelength_nm']} nm" if gen.get("wavelength_nm") else None)
        _print_field("Location A", gen.get("location_a"))
        _print_field("Location B", gen.get("location_b"))
        _print_field("Operator", gen.get("operator"))
        _print_field("Build Cond.", gen.get("build_condition_name"))
        _print_field("Comment", gen.get("comment"))
        print()

    # Acquisition parameters
    acq = parsed.get("acquisition", {})
    if acq and "error" not in acq:
        print("--- Acquisition Parameters ---")
        _print_field("Date/Time", acq.get("datetime"))
        _print_field("Distance Unit", acq.get("units_of_distance"))
        _print_field("Wavelength", f"{acq['actual_wavelength_nm']} nm" if acq.get("actual_wavelength_nm") else None)
        _print_field("Pulse Width", f"{acq['pulse_widths_ns']} ns" if acq.get("pulse_widths_ns") else None)
        _print_field("Group Index", acq.get("group_index"))
        _print_field("Backscatter", f"{acq['backscatter_coefficient_dB']} dB" if acq.get("backscatter_coefficient_dB") is not None else None)
        _print_field("Averages", acq.get("number_of_averages"))
        _print_field("Avg Time", f"{acq['averaging_time_s']} s" if acq.get("averaging_time_s") else None)
        _print_field("Range", f"{acq['range_km']:.3f} km" if acq.get("range_km") else None)
        _print_field("Data Points", acq.get("num_data_points"))
        _print_field("Loss Thresh", f"{acq['loss_threshold_dB']} dB" if acq.get("loss_threshold_dB") is not None else None)
        _print_field("Refl Thresh", f"{acq['reflectance_threshold_dB']} dB" if acq.get("reflectance_threshold_dB") is not None else None)
        _print_field("EOF Thresh", f"{acq['end_of_fiber_threshold_dB']} dB" if acq.get("end_of_fiber_threshold_dB") is not None else None)
        print()

    # Key events
    kevt = parsed.get("key_events", {})
    if kevt and "error" not in kevt:
        num = kevt.get("num_events", 0)
        print(f"--- Key Events ({num}) ---")
        for evt in kevt.get("events", []):
            dist = evt.get("distance_m", 0)
            loss = evt.get("splice_loss_dB", 0)
            refl = evt.get("reflectance_dB", 0)
            etype = evt.get("event_type_description", evt.get("event_type", ""))
            print(f"  #{evt['event_number']:>3d}  {dist:>10.3f} m  "
                  f"loss={loss:+.3f} dB  refl={refl:+.3f} dB  [{etype}]")
            if evt.get("comment"):
                print(f"        comment: {evt['comment']}")
        if kevt.get("total_loss_dB") is not None:
            print(f"\n  Total Loss:  {kevt['total_loss_dB']:.3f} dB")
        if kevt.get("optical_return_loss_dB") is not None:
            print(f"  ORL:         {kevt['optical_return_loss_dB']:.3f} dB")
        if kevt.get("fiber_length_m") is not None:
            print(f"  Fiber Length: {kevt['fiber_length_m']:.3f} m")
        print()

    # Data points summary
    dpts = parsed.get("data_points", {})
    if dpts and "error" not in dpts:
        print("--- Data Points ---")
        _print_field("Total Points", dpts.get("num_data_points"))
        _print_field("Traces", dpts.get("num_traces"))
        print()


def _print_field(label: str, value):
    """Print a labeled field, skipping empty values."""
    if value is not None and value != "":
        print(f"  {label:<15s} {value}")


# --- CLI ---

def main():
    if len(sys.argv) < 2:
        print("Usage: python sor_parser.py <file.sor> [--json] [--pretty]")
        print()
        print("Options:")
        print("  --json     Output as JSON")
        print("  --pretty   Pretty-print JSON (implies --json)")
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
