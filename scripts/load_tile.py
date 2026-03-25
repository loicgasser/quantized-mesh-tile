#!/usr/bin/env python
"""
Performance benchmark for quantized-mesh-tile encode and decode.

Generates grid-based terrain meshes at various resolutions and measures
encode/decode throughput. Prints the overall median runtime in ms.

Usage:
    python load_tile.py                  # run benchmark
    python load_tile.py --quick          # fewer iterations
    python load_tile.py --grids 4,8,16   # custom grid sizes
    python load_tile.py --iters=10       # custom iteration count
"""

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

    lon_step = (east - west) / n
    lat_step = (north - south) / n
    grid = []
    for j in range(n + 1):
        row = []
        for i in range(n + 1):
            lon = west + i * lon_step
            lat = south + j * lat_step
            h = 500.0 * math.sin(lon * 0.05) * math.cos(lat * 0.05) + rng.uniform(-50, 50)
            row.append((lon, lat, h))
        grid.append(row)

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


def run_all(grid_sizes, iterations):
    """Run all benchmarks, return list of all individual timing samples (ms)."""
    geodetic = GlobalGeodetic(True)
    bounds = geodetic.TileBounds(533, 383, 9)
    all_times = []

    # Plain encode/decode at increasing grid sizes
    for n in grid_sizes:
        geometries = make_grid_mesh(n, bounds)
        tile, enc_times = bench_encode(geometries, bounds, iterations)
        all_times.extend(enc_times)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpfile = os.path.join(tmpdir, "tile.terrain")
            tile.toFile(tmpfile)
            _, dec_times = bench_decode(tmpfile, bounds, iterations)
            all_times.extend(dec_times)

    # With lighting extension (largest grid only)
    geometries = make_grid_mesh(grid_sizes[-1], bounds)
    tile, enc_times = bench_encode(geometries, bounds, iterations, hasLighting=True)
    all_times.extend(enc_times)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpfile = os.path.join(tmpdir, "tile.terrain")
        tile.toFile(tmpfile)
        _, dec_times = bench_decode(tmpfile, bounds, iterations, hasLighting=True)
        all_times.extend(dec_times)

    # With watermask (largest grid only)
    tile, enc_times = bench_encode(geometries, bounds, iterations, watermask=[[255]])
    all_times.extend(enc_times)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpfile = os.path.join(tmpdir, "tile.terrain")
        tile.toFile(tmpfile)
        _, dec_times = bench_decode(tmpfile, bounds, iterations, hasWatermask=True)
        all_times.extend(dec_times)

    # Real tiles
    cases = [
        (9, 533, 383, "9_533_383.terrain", {}),
        (9, 769, 319, "9_769_319_watermask.terrain", {"hasWatermask": True}),
        (10, 1563, 590, "10_1563_590_light_watermask.terrain",
         {"hasLighting": True, "hasWatermask": True}),
    ]
    for z, x, y, filename, kw in cases:
        path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(path):
            continue
        tile_bounds = geodetic.TileBounds(x, y, z)
        _, dec_times = bench_decode(path, tile_bounds, iterations, **kw)
        all_times.extend(dec_times)

    return all_times


if __name__ == "__main__":
    quick = "--quick" in sys.argv

    grid_sizes = [4, 8, 16, 32, 64]
    iterations = 20 if not quick else 5

    for arg in sys.argv[1:]:
        if arg.startswith("--grids="):
            grid_sizes = [int(x) for x in arg.split("=")[1].split(",")]
        elif arg.startswith("--iters="):
            iterations = int(arg.split("=")[1])

    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__.strip())
        sys.exit(0)

    all_times = run_all(grid_sizes, iterations)
    median = round(statistics.median(all_times), 3)
    print(f"{median}")
