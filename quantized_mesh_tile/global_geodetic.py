""" This module defines the :class:`quantized_mesh_tile.global_geodetic.GlobalGeodetic`.
Initial code from:
https://svn.osgeo.org/gdal/trunk/gdal/swig/python/scripts/gdal2tiles.py
Functions necessary for generation of global tiles in Plate Carre projection,
EPSG:4326, unprojected profile.
Pixel and tile coordinates are in TMS notation (origin [0,0] in bottom-left).
What coordinate conversions do we need for TMS Global Geodetic tiles?
Global Geodetic tiles are using geodetic coordinates (latitude,longitude)
directly as planar coordinates XY (it is also called Unprojected or Plate
Carre). We need only scaling to pixel pyramid and cutting to tiles.
Pyramid has on top level two tiles, so it is not square but rectangle.
Area [-180,-90,180,90] is scaled to 512x256 pixels.
TMS has coordinate origin (for pixels and tiles) in bottom-left corner.

Reference
---------
"""
from __future__ import division

import math
from builtins import object, range

from past.utils import old_div

MAXZOOMLEVEL = 32


class GlobalGeodetic(object):
    """
    Contructor arguments:

    ``tmscompatible``

        If set to True, defaults the resolution factor to 0.703125 (2 tiles @ level 0)
        Adhers to OSGeo TMS spec and therefore Cesium.
        http://wiki.osgeo.org/wiki/Tile_Map_Service_Specification#global-geodetic
        If set to False, defaults the resolution factor to 1.40625 (1 tile @ level 0)
        Adheres OpenLayers, MapProxy, etc default resolution for WMTS.

    ``tileSize``

        The size of the tile in pixel. Default is `256`.

    """

    def __init__(self, tmscompatible, tileSize=256):
        self.tileSize = tileSize
        if tmscompatible is not None:
            self.resFact = old_div(180.0, self.tileSize)
            self._numberOfLevelZeroTilesX = 2
            self._numberOfLevelZeroTilesY = 1
        else:
            self.resFact = old_div(360.0, self.tileSize)
            self._numberOfLevelZeroTilesX = 1
            self._numberOfLevelZeroTilesY = 1

    def LonLatToPixels(self, lon, lat, zoom):
        "Converts lon/lat to pixel coordinates in given zoom of the EPSG:4326 pyramid"

        res = old_div(self.resFact, 2 ** zoom)
        px = old_div((180 + lon), res)
        py = old_div((90 + lat), res)
        return px, py

    def PixelsToTile(self, px, py):
        "Returns coordinates of the tile covering region in pixel coordinates"

        tx = int(math.ceil(old_div(px, float(self.tileSize))) - 1) if px > 0 else 0
        ty = int(math.ceil(old_div(py, float(self.tileSize))) - 1) if py > 0 else 0
        return tx, ty

    def LonLatToTile(self, lon, lat, zoom):
        "Returns the tile for zoom which covers given lon/lat coordinates"

        px, py = self.LonLatToPixels(lon, lat, zoom)
        return self.PixelsToTile(px, py)

    def Resolution(self, zoom):
        "Resolution (arc/pixel) for given zoom level (measured at Equator)"

        return old_div(self.resFact, 2 ** zoom)
        # return 180 / float( 1 << (8+zoom) )

    def ZoomForPixelSize(self, pixelSize):
        "Maximal scaledown zoom of the pyramid closest to the pixelSize."

        for i in range(MAXZOOMLEVEL):
            if pixelSize > self.Resolution(i):
                if i != 0:
                    return i - 1
                else:
                    return 0  # We don't want to scale up

    def TileBounds(self, tx, ty, zoom):
        "Returns bounds of the given tile"
        res = old_div(self.resFact, 2 ** zoom)
        return (
            tx * self.tileSize * res - 180,
            ty * self.tileSize * res - 90,
            (tx + 1) * self.tileSize * res - 180,
            (ty + 1) * self.tileSize * res - 90
        )

    def TileLatLonBounds(self, tx, ty, zoom):
        "Returns bounds of the given tile in the SWNE form"
        b = self.TileBounds(tx, ty, zoom)
        return (b[1], b[0], b[3], b[2])

    def GetNumberOfXTilesAtZoom(self, zoom):
        "Returns the number of tiles over x at a given zoom level (only 256px)"
        return self._numberOfLevelZeroTilesX << zoom

    def GetNumberOfYTilesAtZoom(self, zoom):
        "Returns the number of tiles over y at a given zoom level (only 256px)"
        return self._numberOfLevelZeroTilesY << zoom
