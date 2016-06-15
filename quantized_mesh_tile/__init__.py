"""
This module provides high level utility functions to encode and decode a terrain tile.

Reference
---------
"""

from .terrain import TerrainTile
from .topology import TerrainTopology


def encode(geometries, bounds=[], watermask=[], hasLighting=False, gzipped=False):
    """
    Function to convert geometries in a quantized-mesh encoded string buffer.

    Arguments:

    ``geometries``

        A list of shapely polygon geometries representing 3 dimensional triangles.
        or
        A list of WKT or WKB Polygons representing 3 dimensional triangles.
        or
        A list of triplet of vertices using the following structure:
        ``(((lon0/lat0/height0),(...),(lon2,lat2,height2)),(...))``

    ``bounds``

        The bounds of the terrain tile. (west, south, east, north)
        If not defined, the bounds will be computed from the provided geometries.

        Default is `[]`.

    ``hasLighting``

        Indicate whether unit vectors should be computed for the lighting extension.

        Default is `False`.

    ``watermask``

        A water mask list (Optional). Adds rendering water effect.
        The water mask list is either one byte, `[0]` for land and `[255]` for
        water, either a list of 256*256 values ranging from 0 to 255.
        Values in the mask are defined from north-to-south and west-to-east.
        Per default no watermask is applied. Note that the water mask effect depends on
        the texture of the raster layer drapped over your terrain.

        Default is `[]`.


    ``gzipped``

        Indicate if the tile content is gzipped.

        Default is `False`.

    """
    topology = TerrainTopology(geometries=geometries, hasLighting=hasLighting)
    if len(bounds) == 4:
        west, south, east, north = bounds
        tile = TerrainTile(watermask=watermask,
            west=west, south=south, east=east, north=north, topology=topology)
    else:
        tile = TerrainTile(watermask=watermask, topology=topology)
    return tile.toStringIO(gzipped=gzipped)


def decode(filePath, bounds, hasLighting=False, hasWatermask=False, gzipped=False):
    """
    Function to convert a quantized-mesh terrain tile file into a
    :class:`quantized_mesh_tile.terrain.TerrainTile` instance.

    Arguments:

    ``filePath``

        An absolute or relative path to write the terrain tile. (Required)
    
    ``bounds``

        The bounds of the terrain tile. (west, south, east, north) (Required).

    ``hasLighting``

        Indicate whether the tile has the lighting extension.

        Default is `False`.

    ``hasWatermask``

        Indicate whether the tile has the water-mask extension.

        Default is `False`.

    """
    west, south, east, north = bounds
    tile = TerrainTile(west=west, south=south, east=east, north=north)
    tile.fromFile(
        filePath, hasLighting=hasLighting, hasWatermask=hasWatermask, gzipped=gzipped)
    return tile
