# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

quantized-mesh-tile is a Python encoder/decoder for terrain tiles following the [Quantized-Mesh format specification](https://github.com/AnalyticalGraphicsInc/quantized-mesh). This format is used by Cesium.js for 3D terrain rendering.

## Common Commands

```bash
# Install development environment
pip install -e ".[dev]"

# Run all tests with coverage
pytest --cov-report term-missing --cov=. tests/

# Run a single test file
pytest tests/test_terrain_tile.py

# Run a specific test
pytest tests/test_terrain_tile.py::test_QuantizedMeshReaderWriter

# Lint with ruff
ruff check ./quantized_mesh_tile ./tests
```

## Architecture

### Core Classes

**TerrainTile** (`terrain.py`) - Main class for reading/writing terrain tiles

- Factory methods: `fromFile()`, `fromBytesIO()`, `fromTerrainTopology()`
- Output methods: `toFile()`, `toBytesIO()`
- Data access: `getVerticesCoordinates()`, `getTrianglesCoordinates()`

**TerrainTopology** (`topology.py`) - Builds mesh topology from geometry inputs

- Accepts Shapely polygons, WKT, WKB, or coordinate tuples
- Handles vertex deduplication and face definition
- Auto-corrects non-triangle geometries

### Data Flow

```text
Input Geometries (Shapely/WKT/WKB/tuples)
    ↓
TerrainTopology (builds vertices, indices, faces)
    ↓
TerrainTile (quantizes, encodes, packs binary)
    ↓
.terrain file (binary output)
```

### Key Modules

- `utils.py` - ZigZag encoding, delta encoding, index encoding (high-water mark)
- `llh_ecef.py` - Lon/Lat/Height to ECEF coordinate conversion (WGS84)
- `bbsphere.py` - Bounding sphere computation (Ritter's algorithm)
- `global_geodetic.py` - TMS-compatible tile coordinate system
- `horizon_occlusion_point.py` - Cesium-style horizon culling calculation

### Extensions

The format supports optional extensions:

- **Lighting**: Unit vectors for surface normals
- **Watermask**: 256x256 or single-byte water mask for rendering

### Coordinate Systems

- Geographic: WGS84 (EPSG:4326)
- Cartesian: ECEF (Earth-Centered, Earth-Fixed)
- Tile System: TMS-compatible, 256x256 pixels per tile
- Vertices quantized to 16-bit unsigned integers (0-65535)

## Dependencies

- `numpy>=2.0.0` - Numerical operations
- `shapely>=2.0.0` - Geometry processing (wheels include GEOS)
