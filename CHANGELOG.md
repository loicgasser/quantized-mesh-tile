# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Roadmap

- Support for encoding/decoding metadata extension ([#43](https://github.com/loicgasser/quantized-mesh-tile/issues/43))

## [0.7.0] - 2025-02-05

### Added

- Custom exception classes for better error handling: `TerrainTileError`, `InvalidGeometryError`, `MissingDimensionError`
- Type hints in `bbsphere.py`
- PyPI long description from README.md
- Pip caching in CI workflow
- ReadTheDocs configuration file (`.readthedocs.yaml`)
- PyPI release workflow (`.github/workflows/release.yml`)

### Changed

- **BREAKING**: Minimum Python version is now 3.9 (dropped support for Python 3.5-3.8)
- **BREAKING**: Minimum dependency versions: `numpy>=2.0.0`, `shapely>=2.0.0`
- Migrated from `setup.py` to `pyproject.toml` (PEP 517/518)
- Replaced flake8/isort with ruff for linting
- Updated GitHub Actions from v2 to v6
- Switched test runner from nose to pytest
- Code style updates: double quotes, trailing commas, improved multi-line formatting
- Performance: Vectorized vertex quantization using numpy in `fromTerrainTopology()`
- Performance: Dict-based edge detection (O(1) lookup instead of O(n) list membership, preserves order)
- Performance: Batch delta encoding using numpy in `_writeTo()`
- Unsupported tile extensions (e.g., metadata) are now skipped with a warning instead of raising an error (fixes [#46](https://github.com/loicgasser/quantized-mesh-tile/issues/46))

### Fixed

- `collapseIntoTriangles` now uses Shapely's Delaunay triangulation, fixing overlapping triangle bug ([#33](https://github.com/loicgasser/quantized-mesh-tile/issues/33))
- Edge indices metadata incorrectly used `indexData32` instead of `EdgeIndices32` for 32-bit tiles
- `BYTESPLIT` constant typo (was 65636, now correctly 65536)
- Mutable default arguments in `encode()` function
- Shadowing of `type` builtin in `utils.py`
- Documentation terrain tile viewer rewritten with modern THREE.js (r160), removing broken Cesium dependency
- Documentation `conf.py` fixes: version update, language setting, removed deprecated mock imports

### Removed

- Shapely speedups import (deprecated in Shapely 2.0, now always enabled)
- Legacy `setup.py`, `setup.cfg`, `dev-requirements.txt`, and `requirements.txt` files

## [0.6.1] - Previous release

See [GitHub releases](https://github.com/loicgasser/quantized-mesh-tile/releases) for earlier versions.

[Unreleased]: https://github.com/loicgasser/quantized-mesh-tile/compare/v0.7.0...HEAD
[0.7.0]: https://github.com/loicgasser/quantized-mesh-tile/compare/v0.6.1...v0.7.0
[0.6.1]: https://github.com/loicgasser/quantized-mesh-tile/releases/tag/v0.6.1
