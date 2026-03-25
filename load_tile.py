#!/usr/bin/env python
"""
Load script demonstrating quantized-mesh-tile encode and decode.

Usage:
    python load_tile.py                         # run all demos
    python load_tile.py <file.terrain> W S E N  # decode an existing .terrain file
"""

import sys
import os
import tempfile

from quantized_mesh_tile import encode, decode
from quantized_mesh_tile.global_geodetic import GlobalGeodetic


# ---------------------------------------------------------------------------
# Sample geometries — vertex tuples (lon, lat, height)
# A full tile covering all 4 edges (2 triangles forming a quad)
# ---------------------------------------------------------------------------
FULL_TILE_GEOMETRIES = [
    "POLYGON Z ((0.0 0.0 1.0, 0.0 1.0 1.0, 1.0 1.0 1.0, 0.0 0.0 1.0))",
    "POLYGON Z ((0.0 0.0 1.0, 1.0 0.0 1.0, 1.0 1.0 1.0, 0.0 0.0 1.0))",
]

# A partial tile with varied heights (vertex tuples) — only west/south edges populated
PARTIAL_TILE_GEOMETRIES = [
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

DATA_DIR = os.path.join(os.path.dirname(__file__), "tests", "data")


def print_tile(tile, label="Tile"):
    """Print a summary of a TerrainTile."""
    print(f"\n--- {label} ---")
    print(f"  Header:   {dict(tile.header)}")
    print(f"  Bounds:   {tile.bounds}")
    print(f"  Vertices: {len(tile.u)} (u) / {len(tile.v)} (v) / {len(tile.h)} (h)")
    print(f"  Indices:  {len(tile.indices)}")
    print(f"  Edges:    west={len(tile.westI)}  south={len(tile.southI)}"
          f"  east={len(tile.eastI)}  north={len(tile.northI)}")
    if hasattr(tile, "vLight") and len(tile.vLight) > 0:
        print(f"  Lighting: {len(tile.vLight)} vertex normals")
    if hasattr(tile, "watermask") and tile.watermask:
        rows = len(tile.watermask)
        if rows and isinstance(tile.watermask[0], (list, tuple)):
            cols = len(tile.watermask[0])
            print(f"  Watermask: {rows}x{cols}")
        else:
            print(f"  Watermask: {rows} byte(s)")
    print(f"  Content-Type: {tile.getContentType()}")
    coords = tile.getVerticesCoordinates()
    print(f"  Vertex coordinates ({len(coords)}):")
    for i, c in enumerate(coords[:10]):
        print(f"    [{i}] {c}")
    if len(coords) > 10:
        print(f"    ... ({len(coords) - 10} more)")


def _tmpfile():
    """Return a path to a non-existent temp .terrain file."""
    d = tempfile.mkdtemp()
    return os.path.join(d, "tile.terrain"), d


def _cleanup(path, dirpath):
    if os.path.exists(path):
        os.unlink(path)
    if os.path.isdir(dirpath):
        os.rmdir(dirpath)


# ---------------------------------------------------------------------------
# 1. Basic encode/decode with vertex tuples (partial tile)
# ---------------------------------------------------------------------------
def demo_basic():
    print("\n" + "=" * 60)
    print("1. BASIC ENCODE/DECODE — vertex tuples, partial tile")
    print("=" * 60)

    geodetic = GlobalGeodetic(True)
    bounds = geodetic.TileBounds(0, 0, 0)

    tile = encode(PARTIAL_TILE_GEOMETRIES, bounds=bounds)
    print_tile(tile, "Encoded (partial, explicit bounds)")

    tmpfile, tmpdir = _tmpfile()
    try:
        tile.toFile(tmpfile)
        print(f"\n  Written: {os.path.getsize(tmpfile)} bytes")
        tile2 = decode(tmpfile, bounds)
        print_tile(tile2, "Decoded back")
    finally:
        _cleanup(tmpfile, tmpdir)


# ---------------------------------------------------------------------------
# 2. WKT input, auto-computed bounds (all 4 edges)
# ---------------------------------------------------------------------------
def demo_wkt():
    print("\n" + "=" * 60)
    print("2. WKT INPUT — full tile, bounds from geometries")
    print("=" * 60)

    tile = encode(FULL_TILE_GEOMETRIES)
    print_tile(tile, "Encoded from WKT (auto bounds)")

    tmpfile, tmpdir = _tmpfile()
    try:
        tile.toFile(tmpfile)
        print(f"\n  Written: {os.path.getsize(tmpfile)} bytes")
        tile2 = decode(tmpfile, tile.bounds)
        print_tile(tile2, "Decoded back")
    finally:
        _cleanup(tmpfile, tmpdir)


# ---------------------------------------------------------------------------
# 3. Encode with lighting extension
# ---------------------------------------------------------------------------
def demo_lighting():
    print("\n" + "=" * 60)
    print("3. LIGHTING EXTENSION — encode with vertex normals")
    print("=" * 60)

    tile = encode(FULL_TILE_GEOMETRIES, hasLighting=True)
    print_tile(tile, "Encoded with lighting")

    tmpfile, tmpdir = _tmpfile()
    try:
        tile.toFile(tmpfile)
        print(f"\n  Written: {os.path.getsize(tmpfile)} bytes")
        tile2 = decode(tmpfile, tile.bounds, hasLighting=True)
        print_tile(tile2, "Decoded with lighting")
    finally:
        _cleanup(tmpfile, tmpdir)


# ---------------------------------------------------------------------------
# 4. Encode with watermask (single-byte: all water)
# ---------------------------------------------------------------------------
def demo_watermask():
    print("\n" + "=" * 60)
    print("4. WATERMASK EXTENSION — single byte (all water)")
    print("=" * 60)

    tile = encode(FULL_TILE_GEOMETRIES, watermask=[[255]])
    print_tile(tile, "Encoded with watermask")

    tmpfile, tmpdir = _tmpfile()
    try:
        tile.toFile(tmpfile)
        print(f"\n  Written: {os.path.getsize(tmpfile)} bytes")
        tile2 = decode(tmpfile, tile.bounds, hasWatermask=True)
        print_tile(tile2, "Decoded with watermask")
    finally:
        _cleanup(tmpfile, tmpdir)


# ---------------------------------------------------------------------------
# 5. Decode real .terrain files from tests/data
# ---------------------------------------------------------------------------
def demo_real_tiles():
    print("\n" + "=" * 60)
    print("5. DECODE REAL .terrain FILES")
    print("=" * 60)

    geodetic = GlobalGeodetic(True)

    # Plain tile (z=9, x=533, y=383) — all 4 edges populated
    z, x, y = 9, 533, 383
    path = os.path.join(DATA_DIR, f"{z}_{x}_{y}.terrain")
    if os.path.exists(path):
        bounds = geodetic.TileBounds(x, y, z)
        tile = decode(path, bounds)
        print_tile(tile, f"Real tile {z}/{x}/{y}")

    # Watermask tile (z=9, x=769, y=319) — 256x256 watermask
    z, x, y = 9, 769, 319
    path = os.path.join(DATA_DIR, f"{z}_{x}_{y}_watermask.terrain")
    if os.path.exists(path):
        bounds = geodetic.TileBounds(x, y, z)
        tile = decode(path, bounds, hasWatermask=True)
        print_tile(tile, f"Real tile {z}/{x}/{y} (watermask)")

    # Lighting + watermask tile (z=10, x=1563, y=590)
    z, x, y = 10, 1563, 590
    path = os.path.join(DATA_DIR, f"{z}_{x}_{y}_light_watermask.terrain")
    if os.path.exists(path):
        bounds = geodetic.TileBounds(x, y, z)
        tile = decode(path, bounds, hasLighting=True, hasWatermask=True)
        print_tile(tile, f"Real tile {z}/{x}/{y} (lighting+watermask)")


# ---------------------------------------------------------------------------
# 6. Decode gzipped .terrain file
# ---------------------------------------------------------------------------
def demo_gzipped():
    print("\n" + "=" * 60)
    print("6. GZIPPED TILE DECODE")
    print("=" * 60)

    geodetic = GlobalGeodetic(True)
    z, x, y = 10, 1563, 590
    path = os.path.join(DATA_DIR, f"{z}_{x}_{y}_light_watermask.terrain.gz")
    if os.path.exists(path):
        bounds = geodetic.TileBounds(x, y, z)
        tile = decode(path, bounds, hasLighting=True, hasWatermask=True, gzipped=True)
        print_tile(tile, f"Gzipped tile {z}/{x}/{y}")
    else:
        print(f"  (skipped — {path} not found)")


# ---------------------------------------------------------------------------
# CLI: decode arbitrary file
# ---------------------------------------------------------------------------
def decode_file(filepath, bounds):
    print(f"=== Decode {filepath} ===")
    tile = decode(filepath, bounds)
    print_tile(tile, filepath)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        demo_basic()
        demo_wkt()
        demo_lighting()
        demo_watermask()
        demo_real_tiles()
        demo_gzipped()
    elif len(sys.argv) == 6:
        filepath = sys.argv[1]
        bounds = tuple(float(v) for v in sys.argv[2:6])
        decode_file(filepath, bounds)
    else:
        print(__doc__.strip())
        sys.exit(1)
