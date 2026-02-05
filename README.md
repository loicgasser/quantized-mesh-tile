quantized-mesh-tile
===================

[![CI](https://github.com/loicgasser/quantized-mesh-tile/actions/workflows/main.yml/badge.svg)](https://github.com/loicgasser/quantized-mesh-tile/actions/workflows/main.yml)
[![Coverage Status](https://coveralls.io/repos/github/loicgasser/quantized-mesh-tile/badge.svg?branch=master)](https://coveralls.io/github/loicgasser/quantized-mesh-tile?branch=master)
[![Doc Status](https://readthedocs.org/projects/quantized-mesh-tile/badge/?version=latest)](http://quantized-mesh-tile.readthedocs.io/en/latest/?badge=latest)

[Quantized-mesh-tile](https://github.com/AnalyticalGraphicsInc/quantized-mesh) is a Python encoder/decoder and topology builder for terrain tiles.

Doc is hosted on Readthedocs: https://quantized-mesh-tile.readthedocs.io/en/latest/

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

## Test Doc Locally

```bash
cd doc
rm -rf build && make htm
python -m http.server 8000 --directory build/html
```

Open `http://localhost:8000/viewer.html`.
