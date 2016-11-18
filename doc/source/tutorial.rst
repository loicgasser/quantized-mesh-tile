.. _tutorial:

Tutorial
========

Introduction
------------

This tutorial shows how to use the quantized mesh tile module.
This format is designed to work exclusively with the `TMS (Tile Map Service)`_ tiling scheme
and is optimized to display `TIN (Triangulated irregular network)`_ data on the web.

.. _TMS (Tile Map Service):
    http://wiki.osgeo.org/wiki/Tile_Map_Service_Specification
.. _TIN (Triangulated irregular network):
    https://en.wikipedia.org/wiki/Triangulated_irregular_network

The only available client able to read and display this format is `Cesium`_.

.. _Cesium:
    http://cesiumjs.org/

This module has been developed based on the specifications of the format described `here`_.

.. _here:
    http://cesiumjs.org/data-and-assets/terrain/formats/quantized-mesh-1.0.html

Therefore, if you've planned on creating your own terrain server, please make sure you follow all the instructions
provided in the specifications of the format. You may also need to define a `layer.json`_ metadata file at the root of your
terrain server which seems to be a derivative of `Mapbox tilejson-spec`_. Make sure you get it right. ;)

.. _layer.json:
    https://assets.agi.com/stk-terrain/tilesets/world/tiles/layer.json
.. _Mapbox tilejson-spec:
    https://github.com/mapbox/tilejson-spec

Create a terrain tile
---------------------

The encoding module can determine the extent of a tile based on the geometries it receives as arguments.
Nevertheless, this can only work if the tile has at least 1 triangle on all of its 4 edges.
As a result, it is advised to always provide the bounds of the tile.

So first determine the extent of the tile.

  >>> from quantized_mesh_tile.global_geodetic import GlobalGeodetic
  >>> geodetic = GlobalGeodetic(True)
  >>> [z, x, y] = [9, 533, 383]
  >>> [west, south, east, north] = bounds = geodetic.TileBounds(x, y, z)

Now that we have the extent, let's assume you generated a mesh using your favorite meshing engine and ended up with
the following geometries.

  >>> geometries = [
          'POLYGON Z ((7.3828125 44.6484375 303.3, ' +
                      '7.3828125 45.0 320.2, ' +
                      '7.5585937 44.82421875 310.2, ' +
                      '7.3828125 44.6484375 303.3))',
          'POLYGON Z ((7.3828125 44.6484375 303.3, ' +
                      '7.734375 44.6484375 350.3, ' +
                      '7.5585937 44.82421875 310.2, ' +
                      '7.3828125 44.6484375 303.3))',
          'POLYGON Z ((7.734375 44.6484375 350.3, ' +
                      '7.734375 45.0 330.3, ' +
                      '7.5585937 44.82421875 310.2, ' +
                      '7.734375 44.6484375 350.3))',
          'POLYGON Z ((7.734375 45.0 330.3, ' +
                      '7.5585937 44.82421875 310.2, ' +
                      '7.3828125 45.0 320.2, ' +
                      '7.734375 45.0 330.3))'
      ]

For a full list of input formats for the geometries, please refer to :class:`quantized_mesh_tile.terrain.TerrainTile`.

  >>> from quantized_mesh_tile import encode
  >>> tile = encode(geometries, bounds=bounds)
  >>> print len(tile.getTrianglesCoordinates())
  >>> tile.toFile('%s/%s/%s.terrain' % (z, x, y))

This operation will write a local file representing the terrain tile.
If you don't want to create a physical file but only need its content, you can use:

  >>> tile = encode(geometries, bounds=bounds)
  >>> content = tile.toStringIO(gzipped=True)

This operation will create a gzipped compressed string buffer wrapped in a `cStringIO.StringIO` instance.

To define a water-mask you can use:

  >>> # Water only
  >>> watermask = [255]
  >>> tile = encode(geometries, bounds=bounds, watermask=watermask)

If you have non-triangular geometries (typically when clipping in an existing mesh),
you can also use the option `autocorrectGeometries` to collapse them into triangles.
This option should be used with care to fix punctual meshing mistakes.

  >>> geometries = [
          'POLYGON Z ((7.3828125 44.6484375 303.3, ' +
                      '7.3828125 45.0 320.2, ' +
                      '7.5585937 44.82421875 310.2, ' +
                      '7.3828125 44.6484375 303.3))',
          'POLYGON Z ((7.3828125 44.6484375 303.3, ' +
                      '7.734375 44.6484375 350.3, ' +
                      '7.5585937 44.82421875 310.2, ' +
                      '7.3828125 44.6484375 303.3))',
          'POLYGON Z ((7.734375 44.6484375 350.3, ' +
                      '7.734375 45.0 330.3, ' +
                      '7.5585937 44.82421875 310.2, ' +
                      '7.734375 44.6484375 350.3))',
          'POLYGON Z ((7.734375 45.0 330.3, ' +
                      '7.5585937 44.82421875 310.2, ' +
                      '7.3828125 45.0 320.2, ' +
                      '7.55859375 45.0 325.2, ' +
                      '7.734375 45.0 330.3))'
      ]
  >>> tile = encode(geometries, bounds=bounds, autocorrectGeometries=True)
  >>> print len(tile.getTrianglesCoordinates())


Read a local terrain tile
-------------------------

As the coordinates within a terrain tile are `quantized`, its values can be only be correctly decoded if we know the exact
extent of the tile.

  >>> from quantized_mesh_tile.global_geodetic import GlobalGeodetic
  >>> geodetic = GlobalGeodetic(True)
  >>> [z, x, y] = [9, 533, 383]
  >>> [west, south, east, north] = bounds = geodetic.TileBounds(x, y, z)
  >>> path = '%s/%s/%s.terrain' % (z, x, y)
  >>> tile = decode(path, bounds)
  >>> print tile.getTrianglesCoordinates()

Or let's assume we have a gizpped compressed tile with water-mask extension:

  >>> tile = decode(path, bounds, gzipped=True, hasWatermask=True)

Read a remote terrain tile
--------------------------

Using the `requests module`_, here is an example on how to read a remote terrain tile.

.. _requests module:
    http://docs.python-requests.org/en/master/

The you won't need to decompress the gzipped tile has this is performed automatically
in the requests module.

  >>> import cStringIO
  >>> import requests
  >>> from quantized_mesh_tile.terrain import TerrainTile
  >>> from quantized_mesh_tile.global_geodetic import GlobalGeodetic
  >>> [z, x, y] = [14, 24297, 10735]
  >>> geodetic = GlobalGeodetic(True)
  >>> [west, south, east, north] = bounds = geodetic.TileBounds(x, y, z)
  >>> url = 'http://assets.agi.com/stk-terrain/world/%s/%s/%s.terrain?v=1.16389.0' % (z, x, y)
  >>> response = requests.get(url)
  >>> content = cStringIO.StringIO(response.content)
  >>> ter = TerrainTile(west=west, south=south, east=east, north=north)
  >>> ter.fromStringIO(content)
  >>> print ter.getVerticesCoordinates()
