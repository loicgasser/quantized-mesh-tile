#!/usr/bin/env python
"""
Performance benchmark for quantized-mesh-tile encode and decode.

Generates grid-based terrain meshes at various resolutions and measures
encode/decode throughput. Outputs JSONL for analysis.

Usage:
    python load_tile.py                  # run full benchmark suite
    python load_tile.py --pretty         # human-readable JSON
    python load_tile.py --quick          # fewer iterations, faster
    python load_tile.py --grids 8,16,32  # custom grid sizes

Examples:
    python load_tile.py | jq 'select(.phase=="encode")'
    python load_tile.py | jq -s 'sort_by(.vertices) | .[] | [.label, .vertices, .median_ms]'
"""

import json
import math
import os
import random
import statistics
import sys
import tempfile
import time

from quantized_mesh_tile import encode, decode
from quantized_mesh_tile.global_geodetic import GlobalGeodetic


DATA_DIR = os.path.join(os.path.dirname(__file__), "tests", "data")


def make_grid_mesh(n, bounds, seed=42):
    """
    Generate a triangulated grid of n x n quads (2 * n^2 triangles).

    Returns a list of vertex-tuple triangles with realistic terrain heights
    spanning the given bounds (west, south, east, north).
    """
    rng = random.Random(seed)
    west, south, east, north = bounds

    # Build (n+1) x (n+1) grid of vertices with perturbed heights
    lon_step = (east - west) / n
    lat_step = (north - south) / n
    grid = []
    for j in range(n + 1):
        row = []
        for i in range(n + 1):
            lon = west + i * lon_step
            lat = south + j * lat_step
            # Terrain-like height: base sine wave + noise
            h = 500.0 * math.sin(lon * 0.05) * math.cos(lat * 0.05) + rng.uniform(-50, 50)
            row.append((lon, lat, h))
        grid.append(row)

    # Triangulate: each quad -> 2 triangles
    triangles = []
    for j in range(n):
        for i in range(n):
            v00 = grid[j][i]
            v10 = grid[j][i + 1]
            v01 = grid[j + 1][i]
            v11 = grid[j + 1][i + 1]
            triangles.append((v00, v10, v01))
            triangles.append((v10, v11, v01))

    return triangles


def bench_encode(geometries, bounds, iterations, **encode_kw):
    """Benchmark encode, return (tile, times_ms)."""
    times = []
    tile = None
    for _ in range(iterations):
        t0 = time.perf_counter()
        tile = encode(geometries, bounds=bounds, **encode_kw)
        times.append((time.perf_counter() - t0) * 1000)
    return tile, times


def bench_decode(filepath, bounds, iterations, **decode_kw):
    """Benchmark decode, return (tile, times_ms)."""
    times = []
    tile = None
    for _ in range(iterations):
        t0 = time.perf_counter()
        tile = decode(filepath, bounds, **decode_kw)
        times.append((time.perf_counter() - t0) * 1000)
    return tile, times


def time_stats(times):
    """Compute stats from a list of ms timings."""
    return {
        "iterations": len(times),
        "mean_ms": round(statistics.mean(times), 3),
        "median_ms": round(statistics.median(times), 3),
        "stdev_ms": round(statistics.stdev(times), 3) if len(times) > 1 else 0.0,
        "min_ms": round(min(times), 3),
        "max_ms": round(max(times), 3),
        "p95_ms": round(sorted(times)[int(len(times) * 0.95)], 3) if len(times) >= 20 else None,
    }


def tile_info(tile):
    """Extract tile structure metrics."""
    has_lighting = hasattr(tile, "vLight") and len(tile.vLight) > 0
    has_watermask = hasattr(tile, "watermask") and bool(tile.watermask)
    watermask_shape = None
    if has_watermask:
        rows = len(tile.watermask)
        if rows and isinstance(tile.watermask[0], (list, tuple)):
            watermask_shape = [rows, len(tile.watermask[0])]
        else:
            watermask_shape = [rows]
    return {
        "vertices": len(tile.u),
        "indices": len(tile.indices),
        "triangles": len(tile.indices) // 3,
        "edge_west": len(tile.westI),
        "edge_south": len(tile.southI),
        "edge_east": len(tile.eastI),
        "edge_north": len(tile.northI),
        "has_lighting": has_lighting,
        "has_watermask": has_watermask,
        "watermask_shape": watermask_shape,
        "height_min": float(tile.header.get("minimumHeight", 0)),
        "height_max": float(tile.header.get("maximumHeight", 0)),
        "bounding_sphere_radius": float(tile.header.get("boundingSphereRadius", 0)),
    }


def emit(record, pretty=False):
    print(json.dumps(record, indent=2 if pretty else None))
    sys.stdout.flush()


def _tmpfile():
    d = tempfile.mkdtemp()
    return os.path.join(d, "tile.terrain"), d


def _cleanup(path, dirpath):
    if os.path.exists(path):
        os.unlink(path)
    if os.path.isdir(dirpath):
        os.rmdir(dirpath)


def bench_grid(grid_n, iterations, bounds, pretty=False, encode_kw=None, decode_kw=None, label_suffix=""):
    """Run encode+decode benchmark for a grid of size n."""
    encode_kw = encode_kw or {}
    decode_kw = decode_kw or {}
    label = f"grid_{grid_n}x{grid_n}{label_suffix}"
    expected_tris = 2 * grid_n * grid_n
    expected_verts = (grid_n + 1) * (grid_n + 1)

    # Generate mesh
    t0 = time.perf_counter()
    geometries = make_grid_mesh(grid_n, bounds)
    gen_ms = (time.perf_counter() - t0) * 1000

    # Encode benchmark
    tile, enc_times = bench_encode(geometries, bounds, iterations, **encode_kw)

    rec = {
        "label": label,
        "phase": "encode",
        "grid_n": grid_n,
        "input_triangles": expected_tris,
        "input_vertices_grid": expected_verts,
        "mesh_gen_ms": round(gen_ms, 3),
        **tile_info(tile),
        **time_stats(enc_times),
    }
    emit(rec, pretty)

    # Write to disk, then decode benchmark
    tmpfile, tmpdir = _tmpfile()
    try:
        tile.toFile(tmpfile)
        fsize = os.path.getsize(tmpfile)

        tile2, dec_times = bench_decode(tmpfile, bounds, iterations, **decode_kw)

        rec = {
            "label": label,
            "phase": "decode",
            "grid_n": grid_n,
            "file_bytes": fsize,
            "bytes_per_vertex": round(fsize / len(tile.u), 1) if tile.u else None,
            **tile_info(tile2),
            **time_stats(dec_times),
        }
        emit(rec, pretty)
    finally:
        _cleanup(tmpfile, tmpdir)


def bench_real_tiles(iterations, pretty=False):
    """Benchmark decoding real .terrain files from tests/data."""
    geodetic = GlobalGeodetic(True)

    cases = [
        ("real_9_533_383", 9, 533, 383, "9_533_383.terrain", {}),
        ("real_9_769_319_wm", 9, 769, 319, "9_769_319_watermask.terrain",
         {"hasWatermask": True}),
        ("real_10_1563_590_light_wm", 10, 1563, 590,
         "10_1563_590_light_watermask.terrain",
         {"hasLighting": True, "hasWatermask": True}),
    ]
    for label, z, x, y, filename, kw in cases:
        path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(path):
            continue
        bounds = geodetic.TileBounds(x, y, z)
        fsize = os.path.getsize(path)
        tile, dec_times = bench_decode(path, bounds, iterations, **kw)
        rec = {
            "label": label,
            "phase": "decode",
            "file_bytes": fsize,
            "bytes_per_vertex": round(fsize / len(tile.u), 1) if tile.u else None,
            **tile_info(tile),
            **time_stats(dec_times),
        }
        emit(rec, pretty)


def run_all(grid_sizes, iterations, pretty=False):
    geodetic = GlobalGeodetic(True)
    # Use a realistic tile bounds (Swiss Alps area, same as test tile 9/533/383)
    bounds = geodetic.TileBounds(533, 383, 9)  # [7.38, 44.65, 7.73, 45.0]

    # Plain encode/decode at increasing grid sizes
    for n in grid_sizes:
        bench_grid(n, iterations, bounds, pretty=pretty)

    # With lighting extension
    for n in grid_sizes:
        bench_grid(n, iterations, bounds, pretty=pretty,
                   encode_kw={"hasLighting": True},
                   decode_kw={"hasLighting": True},
                   label_suffix="_light")

    # With watermask (single-byte)
    bench_grid(grid_sizes[-1], iterations, bounds, pretty=pretty,
               encode_kw={"watermask": [[255]]},
               decode_kw={"hasWatermask": True},
               label_suffix="_wm")

    # Real tiles
    bench_real_tiles(iterations, pretty=pretty)


if __name__ == "__main__":
    pretty = "--pretty" in sys.argv
    quick = "--quick" in sys.argv

    grid_sizes = [8, 16, 32, 64, 128]
    iterations = 50 if not quick else 5

    # Parse --grids flag
    for arg in sys.argv[1:]:
        if arg.startswith("--grids="):
            grid_sizes = [int(x) for x in arg.split("=")[1].split(",")]
        elif arg.startswith("--iters="):
            iterations = int(arg.split("=")[1])

    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__.strip())
        sys.exit(0)

    run_all(grid_sizes, iterations, pretty=pretty)
