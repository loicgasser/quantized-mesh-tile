#!/usr/bin/env python
"""
Load script for quantized-mesh-tile encode and decode.

Outputs JSON (one object per line) for easy analysis with jq, pandas, etc.

Usage:
    python load_tile.py                         # run all demos, JSON to stdout
    python load_tile.py <file.terrain> W S E N  # decode a single file
    python load_tile.py --pretty                # pretty-print JSON

Examples:
    python load_tile.py | jq '.vertices_count'
    python load_tile.py | jq 'select(.has_lighting)'
    python load_tile.py | python -c "import sys,json,pandas as pd; \\
        print(pd.DataFrame(json.loads(l) for l in sys.stdin).to_string())"
"""

import json
import os
import sys
import tempfile
import time

from quantized_mesh_tile import encode, decode
from quantized_mesh_tile.global_geodetic import GlobalGeodetic


DATA_DIR = os.path.join(os.path.dirname(__file__), "tests", "data")

FULL_TILE_WKT = [
    "POLYGON Z ((0.0 0.0 1.0, 0.0 1.0 1.0, 1.0 1.0 1.0, 0.0 0.0 1.0))",
    "POLYGON Z ((0.0 0.0 1.0, 1.0 0.0 1.0, 1.0 1.0 1.0, 0.0 0.0 1.0))",
]

PARTIAL_TILE_TUPLES = [
    ((-168.755, -33.753, 15.793),
     (-180.0, -45.004, 3.1),
     (-157.504, -45.004, -7.144)),
    ((-180.0, -33.753, 38.954),
     (-180.0, -45.004, 3.1),
     (-168.755, -33.753, 15.793)),
    ((-180.0, -33.753, 38.954),
     (-168.755, -33.753, 15.793),
     (-180.0, -22.503, 50.312)),
]


def tile_metrics(tile, label, phase, file_bytes=None, elapsed_ms=None):
    """Extract a flat dict of metrics from a TerrainTile."""
    header = {k: float(v) for k, v in tile.header.items()}
    bounds = [float(b) for b in tile.bounds]

    has_lighting = hasattr(tile, "vLight") and len(tile.vLight) > 0
    has_watermask = hasattr(tile, "watermask") and bool(tile.watermask)
    watermask_shape = None
    if has_watermask:
        rows = len(tile.watermask)
        if rows and isinstance(tile.watermask[0], (list, tuple)):
            watermask_shape = [rows, len(tile.watermask[0])]
        else:
            watermask_shape = [rows]

    m = {
        "label": label,
        "phase": phase,
        "bounds": bounds,
        "vertices_count": len(tile.u),
        "indices_count": len(tile.indices),
        "triangles_count": len(tile.indices) // 3,
        "edge_west": len(tile.westI),
        "edge_south": len(tile.southI),
        "edge_east": len(tile.eastI),
        "edge_north": len(tile.northI),
        "edge_total": len(tile.westI) + len(tile.southI) + len(tile.eastI) + len(tile.northI),
        "has_lighting": has_lighting,
        "has_watermask": has_watermask,
        "watermask_shape": watermask_shape,
        "content_type": tile.getContentType(),
        "height_min": header.get("minimumHeight"),
        "height_max": header.get("maximumHeight"),
        "height_range": header.get("maximumHeight", 0) - header.get("minimumHeight", 0),
        "bounding_sphere_radius": header.get("boundingSphereRadius"),
    }
    if file_bytes is not None:
        m["file_bytes"] = file_bytes
    if elapsed_ms is not None:
        m["elapsed_ms"] = round(elapsed_ms, 3)
    return m


def emit(record, pretty=False):
    print(json.dumps(record, indent=2 if pretty else None))


def _tmpfile():
    d = tempfile.mkdtemp()
    return os.path.join(d, "tile.terrain"), d


def _cleanup(path, dirpath):
    if os.path.exists(path):
        os.unlink(path)
    if os.path.isdir(dirpath):
        os.rmdir(dirpath)


def _timed_encode(geometries, **kwargs):
    t0 = time.perf_counter()
    tile = encode(geometries, **kwargs)
    return tile, (time.perf_counter() - t0) * 1000


def _timed_decode(path, bounds, **kwargs):
    t0 = time.perf_counter()
    tile = decode(path, bounds, **kwargs)
    return tile, (time.perf_counter() - t0) * 1000


def roundtrip(label, geometries, encode_kw=None, decode_kw=None, pretty=False):
    """Encode geometries, write to disk, decode back, emit metrics for each phase."""
    encode_kw = encode_kw or {}
    decode_kw = decode_kw or {}

    tile, enc_ms = _timed_encode(geometries, **encode_kw)
    emit(tile_metrics(tile, label, "encode", elapsed_ms=enc_ms), pretty)

    tmpfile, tmpdir = _tmpfile()
    try:
        tile.toFile(tmpfile)
        fsize = os.path.getsize(tmpfile)
        tile2, dec_ms = _timed_decode(tmpfile, tile.bounds, **decode_kw)
        emit(tile_metrics(tile2, label, "decode", file_bytes=fsize, elapsed_ms=dec_ms), pretty)
    finally:
        _cleanup(tmpfile, tmpdir)


def decode_real(label, z, x, y, filename, decode_kw=None, pretty=False):
    """Decode a real .terrain file from tests/data."""
    decode_kw = decode_kw or {}
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return
    geodetic = GlobalGeodetic(True)
    bounds = geodetic.TileBounds(x, y, z)
    fsize = os.path.getsize(path)
    tile, dec_ms = _timed_decode(path, bounds, **decode_kw)
    emit(tile_metrics(tile, label, "decode", file_bytes=fsize, elapsed_ms=dec_ms), pretty)


def run_all(pretty=False):
    geodetic = GlobalGeodetic(True)

    # 1. Basic — vertex tuples, partial tile, explicit bounds
    roundtrip(
        "basic_partial",
        PARTIAL_TILE_TUPLES,
        encode_kw={"bounds": geodetic.TileBounds(0, 0, 0)},
        pretty=pretty,
    )

    # 2. WKT — full tile, auto bounds
    roundtrip("wkt_full", FULL_TILE_WKT, pretty=pretty)

    # 3. Lighting extension
    roundtrip(
        "lighting",
        FULL_TILE_WKT,
        encode_kw={"hasLighting": True},
        decode_kw={"hasLighting": True},
        pretty=pretty,
    )

    # 4. Watermask extension
    roundtrip(
        "watermask",
        FULL_TILE_WKT,
        encode_kw={"watermask": [[255]]},
        decode_kw={"hasWatermask": True},
        pretty=pretty,
    )

    # 5. Real terrain files
    decode_real("real_9_533_383", 9, 533, 383,
                "9_533_383.terrain", pretty=pretty)
    decode_real("real_9_769_319_watermask", 9, 769, 319,
                "9_769_319_watermask.terrain",
                decode_kw={"hasWatermask": True}, pretty=pretty)
    decode_real("real_10_1563_590_light_wm", 10, 1563, 590,
                "10_1563_590_light_watermask.terrain",
                decode_kw={"hasLighting": True, "hasWatermask": True}, pretty=pretty)

    # 6. Gzipped
    decode_real("gzipped_10_1563_590", 10, 1563, 590,
                "10_1563_590_light_watermask.terrain.gz",
                decode_kw={"hasLighting": True, "hasWatermask": True, "gzipped": True},
                pretty=pretty)


def decode_file(filepath, bounds, pretty=False):
    fsize = os.path.getsize(filepath)
    tile, dec_ms = _timed_decode(filepath, bounds)
    emit(tile_metrics(tile, filepath, "decode", file_bytes=fsize, elapsed_ms=dec_ms), pretty)


if __name__ == "__main__":
    pretty = "--pretty" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--pretty"]

    if len(args) == 0:
        run_all(pretty=pretty)
    elif len(args) == 5:
        decode_file(args[0], tuple(float(v) for v in args[1:5]), pretty=pretty)
    else:
        print(__doc__.strip())
        sys.exit(1)
