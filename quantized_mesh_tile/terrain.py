""" This module defines the :class:`quantized_mesh_tile.terrain.TerrainTile`.
More information about the format specification can be found here:
http://cesiumjs.org/data-and-assets/terrain/formats/quantized-mesh-1.0.html

Reference
---------
"""
from __future__ import absolute_import
from __future__ import division

from future import standard_library
standard_library.install_aliases()
from builtins import next
from builtins import map
from builtins import range
from builtins import object
from past.utils import old_div
import os
import gzip
import io
from collections import OrderedDict
from . import horizon_occlusion_point as occ
from .utils import (
    octEncode, octDecode, zigZagDecode, zigZagEncode,
    gzipFileObject, ungzipFileObject, unpackEntry, unpackIndices,
    decodeIndices, packEntry, packIndices, encodeIndices
)
from .bbsphere import BoundingSphere
from .topology import TerrainTopology

MAX = 32767.0
# For a tile of 256px * 256px
TILEPXS = 65536


def lerp(p, q, time):
    return ((1.0 - time) * p) + (time * q)


class TerrainTile(object):
    """
    The main class to read and write a terrain tile.

    Constructor arguments:

    ``west``

        The longitude at the western edge of the tile. Default is `-1.0`.

    ``east``

        The longitude at the eastern edge of the tile. Default is `1.0`.

    ``south``

        The latitude at the southern edge of the tile. Default is `-1.0`.

    ``north``

        The latitude at the northern edge of the tile. Default is `1.0`.

    ``topology``

        The topology of the mesh which but be an instance of
        :class:`quantized_mesh_tile.topology.TerrainTopology`. Default is `None`.

    ``watermask``
        A water mask list (Optional). Adds rendering water effect.
        The water mask list is either one byte, `[0]` for land and `[255]` for
        water, either a list of 256*256 values ranging from 0 to 255.
        Values in the mask are defined from north-to-south and west-to-east.
        Per default no watermask is applied. Note that the water mask effect depends on
        the texture of the raster layer drapped over your terrain.
        Default is `[]`.

    Usage examples::

        from quantized_mesh_tile.terrain import TerrainTile
        from quantized_mesh_tile.topology import TerrainTopology
        from quantized_mesh_tile.global_geodetic import GlobalGeodetic

        # The tile coordinates
        x = 533
        y = 383
        z = 9
        geodetic = GlobalGeodetic(True)
        [west, south, east, north] = geodetic.TileBounds(x, y, z)

        # Read a terrain tile (unzipped)
        tile = TerrainTile(west=west, south=south, east=east, north=north)
        tile.fromFile('mytile.terrain')

        # Write a terrain tile locally from scratch (lon/lat/height)
        wkts = [
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
        topology = TerrainTopology(geometries=wkts)
        tile = TerrainTile(topology=topology)
        tile.toFile('mytile.terrain')

    """
    quantizedMeshHeader = OrderedDict([
        ['centerX', 'd'],  # 8bytes
        ['centerY', 'd'],
        ['centerZ', 'd'],
        ['minimumHeight', 'f'],  # 4bytes
        ['maximumHeight', 'f'],
        ['boundingSphereCenterX', 'd'],
        ['boundingSphereCenterY', 'd'],
        ['boundingSphereCenterZ', 'd'],
        ['boundingSphereRadius', 'd'],
        ['horizonOcclusionPointX', 'd'],
        ['horizonOcclusionPointY', 'd'],
        ['horizonOcclusionPointZ', 'd']
    ])

    vertexData = OrderedDict([
        ['vertexCount', 'I'],  # 4bytes -> determines the size of the 3 following arrays
        ['uVertexCount', 'H'],  # 2bytes, unsigned short
        ['vVertexCount', 'H'],
        ['heightVertexCount', 'H']
    ])

    indexData16 = OrderedDict([
        ['triangleCount', 'I'],
        ['indices', 'H']
    ])
    indexData32 = OrderedDict([
        ['triangleCount', 'I'],
        ['indices', 'I']
    ])

    EdgeIndices16 = OrderedDict([
        ['westVertexCount', 'I'],
        ['westIndices', 'H'],
        ['southVertexCount', 'I'],
        ['southIndices', 'H'],
        ['eastVertexCount', 'I'],
        ['eastIndices', 'H'],
        ['northVertexCount', 'I'],
        ['northIndices', 'H']
    ])
    EdgeIndices32 = OrderedDict([
        ['westVertexCount', 'I'],
        ['westIndices', 'I'],
        ['southVertexCount', 'I'],
        ['southIndices', 'I'],
        ['eastVertexCount', 'I'],
        ['eastIndices', 'I'],
        ['northVertexCount', 'I'],
        ['northIndices', 'I']
    ])

    ExtensionHeader = OrderedDict([
        ['extensionId', 'B'],
        ['extensionLength', 'I']
    ])

    OctEncodedVertexNormals = OrderedDict([
        ['xy', 'B']
    ])

    WaterMask = OrderedDict([
        ['xy', 'B']
    ])

    BYTESPLIT = 65636

    # Coordinates are given in lon/lat WSG84
    def __init__(self, *args, **kwargs):
        self._west = kwargs.get('west', -1.0)
        self._east = kwargs.get('east', 1.0)
        self._south = kwargs.get('south', -1.0)
        self._north = kwargs.get('north', 1.0)
        self._longs = []
        self._lats = []
        self._heights = []
        self._triangles = []
        self.EPSG = 4326

        # Extensions
        self.vLight = []
        self.watermask = kwargs.get('watermask', [])
        self.hasWatermask = kwargs.get('hasWatermask', bool(len(self.watermask) > 0))

        self.header = OrderedDict()
        for k, v in TerrainTile.quantizedMeshHeader.items():
            self.header[k] = 0.0
        self.u = []
        self.v = []
        self.h = []
        self.indices = []
        self.westI = []
        self.southI = []
        self.eastI = []
        self.northI = []

        topology = kwargs.get('topology')
        if topology is not None:
            self.fromTerrainTopology(topology)

    def __repr__(self):
        msg = 'Header: %s\n' % self.header
        # Output intermediate structure
        msg += '\nVertexCount: %s' % len(self.u)
        msg += '\nuVertex: %s' % self.u
        msg += '\nvVertex: %s' % self.v
        msg += '\nhVertex: %s' % self.h
        msg += '\nindexDataCount: %s' % len(self.indices)
        msg += '\nindexData: %s' % self.indices
        msg += '\nwestIndicesCount: %s' % len(self.westI)
        msg += '\nwestIndices: %s' % self.westI
        msg += '\nsouthIndicesCount: %s' % len(self.southI)
        msg += '\nsouthIndices: %s' % self.southI
        msg += '\neastIndicesCount: %s' % len(self.eastI)
        msg += '\neastIndices: %s' % self.eastI
        msg += '\nnorthIndicesCount: %s' % len(self.northI)
        msg += '\nnorthIndices: %s\n' % self.northI
        # Output coordinates
        msg += '\nNumber of triangles: %s' % (old_div(len(self.indices), 3))
        msg += '\nTriangles coordinates in EPSG %s' % self.EPSG
        msg += '\n%s' % self.getTrianglesCoordinates()

        return msg

    def getContentType(self):
        """
        A method to determine the content type of a tile.
        """
        baseContent = 'application/vnd.quantized-mesh'
        if self.hasLighting and self.hasWatermask:
            return baseContent + ';extensions=octvertexnormals-watermask'
        elif self.hasLighting:
            return baseContent + ';extensions=octvertexnormals'
        elif self.hasWatermask:
            return baseContent + ';extensions=watermask'
        else:
            return baseContent

    def getVerticesCoordinates(self):
        """
        A method to retrieve the coordinates of the vertices in lon,lat,height.
        """
        coordinates = []
        self._computeVerticesCoordinates()
        for i, lon in enumerate(self._longs):
            coordinates.append((lon, self._lats[i], self._heights[i]))
        return coordinates

    def getTrianglesCoordinates(self):
        """
        A method to retrieve triplet of coordinates representing the triangles
        in lon,lat,height.
        """
        triangles = []
        self._computeVerticesCoordinates()
        indices = iter(self.indices)
        for i in range(0, len(self.indices) - 1, 3):
            vi1 = next(indices)
            vi2 = next(indices)
            vi3 = next(indices)
            triangle = (
                (self._longs[vi1],
                 self._lats[vi1],
                 self._heights[vi1]),
                (self._longs[vi2],
                 self._lats[vi2],
                 self._heights[vi2]),
                (self._longs[vi3],
                 self._lats[vi3],
                 self._heights[vi3])
            )
            triangles.append(triangle)
        if len(list(indices)) > 0:
            raise Exception('Corrupted tile')
        return triangles

    def _computeVerticesCoordinates(self):
        """
        A private method to compute the vertices coordinates.
        """
        if len(self._longs) == 0:
            for u in self.u:
                self._longs.append(lerp(self._west, self._east, old_div(float(u), MAX)))
            for v in self.v:
                self._lats.append(lerp(self._south, self._north, old_div(float(v), MAX)))
            for h in self.h:
                self._heights.append(
                    lerp(
                        self.header['minimumHeight'],
                        self.header['maximumHeight'],
                        old_div(float(h), MAX)
                    )
                )

    def fromStringIO(self, f, hasLighting=False, hasWatermask=False):
        """
        A method to read a terrain tile content.

        Arguments:

        ``f``

            An instance of cStringIO.StingIO containing the terrain data. (Required)

        ``hasLighting``

            Indicate if the tile contains lighting information. Default is ``False``.

        ``hasWatermask``

            Indicate if the tile contains watermask information. Default is ``False``.
        """
        self.hasLighting = hasLighting
        self.hasWatermask = hasWatermask
        # Header
        for k, v in TerrainTile.quantizedMeshHeader.items():
            self.header[k] = unpackEntry(f, v)

        # Delta decoding
        ud = 0
        vd = 0
        hd = 0
        # Vertices
        vertexCount = unpackEntry(f, TerrainTile.vertexData['vertexCount'])
        for i in range(0, vertexCount):
            ud += zigZagDecode(
                unpackEntry(f, TerrainTile.vertexData['uVertexCount'])
            )
            self.u.append(ud)
        for i in range(0, vertexCount):
            vd += zigZagDecode(
                unpackEntry(f, TerrainTile.vertexData['vVertexCount'])
            )
            self.v.append(vd)
        for i in range(0, vertexCount):
            hd += zigZagDecode(
                unpackEntry(f, TerrainTile.vertexData['heightVertexCount'])
            )
            self.h.append(hd)

        # Indices
        meta = TerrainTile.indexData16
        if vertexCount > TerrainTile.BYTESPLIT:
            meta = TerrainTile.indexData32
        triangleCount = unpackEntry(f, meta['triangleCount'])
        ind = unpackIndices(f, triangleCount * 3, meta['indices'])
        self.indices = decodeIndices(ind)

        meta = TerrainTile.EdgeIndices16
        if vertexCount > TerrainTile.BYTESPLIT:
            meta = TerrainTile.indexData32
        # Edges (vertices on the edge of the tile)
        # Indices (are the also high water mark encoded?)
        westIndicesCount = unpackEntry(f, meta['westVertexCount'])
        self.westI = unpackIndices(f, westIndicesCount, meta['westIndices'])

        southIndicesCount = unpackEntry(f, meta['southVertexCount'])
        self.southI = unpackIndices(f, southIndicesCount, meta['southIndices'])

        eastIndicesCount = unpackEntry(f, meta['eastVertexCount'])
        self.eastI = unpackIndices(f, eastIndicesCount, meta['eastIndices'])

        northIndicesCount = unpackEntry(f, meta['northVertexCount'])
        self.northI = unpackIndices(f, northIndicesCount, meta['northIndices'])

        if self.hasLighting:
            # One byte of padding
            # Light extension header
            meta = TerrainTile.ExtensionHeader
            extensionId = unpackEntry(f, meta['extensionId'])
            if extensionId == 1:
                extensionLength = unpackEntry(f, meta['extensionLength'])

                # Consider padding of 2 bits
                # http://cesiumjs.org/data-and-assets/terrain/formats/quantized-mesh-1.0.html
                f.read(2)

                for i in range(0, (old_div(extensionLength, 2)) - 1):
                    x = unpackEntry(f, TerrainTile.OctEncodedVertexNormals['xy'])
                    y = unpackEntry(f, TerrainTile.OctEncodedVertexNormals['xy'])
                    self.vLight.append(octDecode(x, y))

        if self.hasWatermask:
            meta = TerrainTile.ExtensionHeader
            extensionId = unpackEntry(f, meta['extensionId'])
            if extensionId == 2:
                extensionLength = unpackEntry(f, meta['extensionLength'])
                row = []
                for i in range(0, extensionLength):
                    row.append(unpackEntry(f, TerrainTile.WaterMask['xy']))
                    if len(row) == 256:
                        self.watermask.append(row)
                        row = []
                if len(row) > 0:
                    self.watermask.append(row)

        data = f.read(1)
        if data:
            raise Exception('Should have reached end of file, but didn\'t')

    def fromFile(self, filePath, hasLighting=False, hasWatermask=False, gzipped=False):
        """
        A method to read a terrain tile file. It is assumed that the tile unzipped.

        Arguments:

        ``filePath``

            An absolute or relative path to a quantized-mesh terrain tile. (Required)

        ``hasLighting``

            Indicate if the tile contains lighting information. Default is ``False``.

        ``hasWatermask``

            Indicate if the tile contains watermask information. Default is ``False``.

        ``gzipped``

            Indicate if the tile content is gzipped. Default is ``False``.
        """
        with open(filePath, 'rb') as f:
            if gzipped:
                f = ungzipFileObject(f)
            self.fromStringIO(f, hasLighting=hasLighting, hasWatermask=hasWatermask)

    def toStringIO(self, gzipped=False):
        """
        A method to write the terrain tile data to a file-like object (a string buffer).

        Arguments:

        ``gzipped``

            Indicate if the content should be gzipped. Default is ``False``.
        """
        f = io.StringIO()
        self._writeTo(f)
        if gzipped:
            f = gzipFileObject(f)
        return f

    def toFile(self, filePath, gzipped=False):
        """
        A method to write the terrain tile data to a physical file.

        Argument:

        ``filePath``

            An absolute or relative path to write the terrain tile. (Required)

        ``gzipped``

            Indicate if the content should be gzipped. Default is ``False``.
        """
        if os.path.isfile(filePath):
            raise IOError('File %s already exists' % filePath)

        if not gzipped:
            with open(filePath, 'wb') as f:
                self._writeTo(f)
        else:
            with gzip.open(filePath, 'wb') as f:
                self._writeTo(f)

    def _writeTo(self, f):
        """
        A private method to write the terrain tile to a file or file-like object.
        """
        # Header
        for k, v in TerrainTile.quantizedMeshHeader.items():
            f.write(packEntry(v, self.header[k]))

        # Delta decoding
        vertexCount = len(self.u)
        # Vertices
        f.write(packEntry(TerrainTile.vertexData['vertexCount'], vertexCount))
        # Move the initial value
        f.write(
            packEntry(TerrainTile.vertexData['uVertexCount'], zigZagEncode(self.u[0]))
        )
        for i in range(0, vertexCount - 1):
            ud = self.u[i + 1] - self.u[i]
            f.write(packEntry(TerrainTile.vertexData['uVertexCount'], zigZagEncode(ud)))
        f.write(
            packEntry(TerrainTile.vertexData['uVertexCount'], zigZagEncode(self.v[0]))
        )
        for i in range(0, vertexCount - 1):
            vd = self.v[i + 1] - self.v[i]
            f.write(packEntry(TerrainTile.vertexData['vVertexCount'], zigZagEncode(vd)))
        f.write(
            packEntry(TerrainTile.vertexData['uVertexCount'], zigZagEncode(self.h[0]))
        )
        for i in range(0, vertexCount - 1):
            hd = self.h[i + 1] - self.h[i]
            f.write(
                packEntry(TerrainTile.vertexData['heightVertexCount'], zigZagEncode(hd))
            )

        # Indices
        meta = TerrainTile.indexData16
        if vertexCount > TerrainTile.BYTESPLIT:
            meta = TerrainTile.indexData32

        f.write(packEntry(meta['triangleCount'], old_div(len(self.indices), 3)))
        ind = encodeIndices(self.indices)
        packIndices(f, meta['indices'], ind)

        meta = TerrainTile.EdgeIndices16
        if vertexCount > TerrainTile.BYTESPLIT:
            meta = TerrainTile.EdgeIndices32

        f.write(packEntry(meta['westVertexCount'], len(self.westI)))
        for wi in self.westI:
            f.write(packEntry(meta['westIndices'], wi))

        f.write(packEntry(meta['southVertexCount'], len(self.southI)))
        for si in self.southI:
            f.write(packEntry(meta['southIndices'], si))

        f.write(packEntry(meta['eastVertexCount'], len(self.eastI)))
        for ei in self.eastI:
            f.write(packEntry(meta['eastIndices'], ei))

        f.write(packEntry(meta['northVertexCount'], len(self.northI)))
        for ni in self.northI:
            f.write(packEntry(meta['northIndices'], ni))

        # Extension header for light
        if len(self.vLight) > 0:
            self.hasLighting = True
            meta = TerrainTile.ExtensionHeader
            # Extension header ID is 1 for lightening
            f.write(packEntry(meta['extensionId'], 1))
            # Unsigned char size len is 1
            f.write(packEntry(meta['extensionLength'], 2 * vertexCount))

            # Add 2 bytes of padding
            f.write(packEntry('B', 1))
            f.write(packEntry('B', 1))

            metaV = TerrainTile.OctEncodedVertexNormals
            for i in range(0, vertexCount - 1):
                x, y = octEncode(self.vLight[i])
                f.write(packEntry(metaV['xy'], x))
                f.write(packEntry(metaV['xy'], y))

        if len(self.watermask) > 0:
            self.hasWatermask = True
            # Extension header ID is 2 for watermark
            meta = TerrainTile.ExtensionHeader
            f.write(packEntry(meta['extensionId'], 2))
            # Extension header meta
            nbRows = len(self.watermask)
            if nbRows > 1:
                # Unsigned char size len is 1
                f.write(packEntry(meta['extensionLength'], TILEPXS))
                if nbRows != 256:
                    raise Exception(
                        'Unexpected number of rows for the watermask: %s' % nbRows
                    )
                # From North to South
                for i in range(0, nbRows):
                    x = self.watermask[i]
                    if len(x) != 256:
                        raise Exception(
                            'Unexpected number of columns for the watermask: %s' % len(x)
                        )
                    # From West to East
                    for y in x:
                        f.write(packEntry(TerrainTile.WaterMask['xy'], int(y)))
            else:
                f.write(packEntry(meta['extensionLength'], 1))
                if self.watermask[0][0] is None:
                    self.watermask[0][0] = 0
                f.write(packEntry(TerrainTile.WaterMask['xy'], int(self.watermask[0][0])))

    def fromTerrainTopology(self, topology, bounds=None):
        """
        A method to prepare a terrain tile data structure.

        Arguments:

        ``topology``

            The topology of the mesh which must be an instance of
            :class:`quantized_mesh_tile.topology.TerrainTopology`. (Required)

        ``bounds``

            The bounds of a the terrain tile. (west, south, east, north)
            If not defined, the bounds defined during initialization will be used.
            If no bounds are provided, then the bounds
            are extracted from the topology object.

        """
        if not isinstance(topology, TerrainTopology):
            raise Exception('topology object must be an instance of TerrainTopology')

        # If the bounds are not provided use
        # topology extent instead
        if bounds is not None:
            self._west = bounds[0]
            self._east = bounds[2]
            self._south = bounds[1]
            self._north = bounds[3]
        elif len(set([self._west, self._south, self._east, self._north]).difference(
                set([-1.0, -1.0, 1.0, 1.0]))) != 0:
            # Bounds already defined earlier
            pass
        else:
            # Set tile bounds
            self._west = topology.minLon
            self._east = topology.maxLon
            self._south = topology.minLat
            self._north = topology.maxLat

        bSphere = BoundingSphere()
        bSphere.fromPoints(topology.cartesianVertices)

        ecefMinX = topology.ecefMinX
        ecefMinY = topology.ecefMinY
        ecefMinZ = topology.ecefMinZ
        ecefMaxX = topology.ecefMaxX
        ecefMaxY = topology.ecefMaxY
        ecefMaxZ = topology.ecefMaxZ

        # Center of the bounding box 3d (TODO verify)
        centerCoords = [
            ecefMinX + (ecefMaxX - ecefMinX) * 0.5,
            ecefMinY + (ecefMaxY - ecefMinY) * 0.5,
            ecefMinZ + (ecefMaxZ - ecefMinZ) * 0.5
        ]

        occlusionPCoords = occ.fromPoints(topology.cartesianVertices, bSphere)

        for k, v in TerrainTile.quantizedMeshHeader.items():
            if k == 'centerX':
                self.header[k] = centerCoords[0]
            elif k == 'centerY':
                self.header[k] = centerCoords[1]
            elif k == 'centerZ':
                self.header[k] = centerCoords[2]
            elif k == 'minimumHeight':
                self.header[k] = topology.minHeight
            elif k == 'maximumHeight':
                self.header[k] = topology.maxHeight
            elif k == 'boundingSphereCenterX':
                self.header[k] = bSphere.center[0]
            elif k == 'boundingSphereCenterY':
                self.header[k] = bSphere.center[1]
            elif k == 'boundingSphereCenterZ':
                self.header[k] = bSphere.center[2]
            elif k == 'boundingSphereRadius':
                self.header[k] = bSphere.radius
            elif k == 'horizonOcclusionPointX':
                self.header[k] = occlusionPCoords[0]
            elif k == 'horizonOcclusionPointY':
                self.header[k] = occlusionPCoords[1]
            elif k == 'horizonOcclusionPointZ':
                self.header[k] = occlusionPCoords[2]

        bLon = old_div(MAX, (self._east - self._west))
        bLat = old_div(MAX, (self._north - self._south))

        quantizeLonIndices = lambda x: int(round((x - self._west) * bLon))
        quantizeLatIndices = lambda x: int(round((x - self._south) * bLat))

        deniv = self.header['maximumHeight'] - self.header['minimumHeight']
        # In case a tile is completely flat
        if deniv == 0:
            quantizeHeightIndices = lambda x: 0
        else:
            bHeight = old_div(MAX, deniv)
            quantizeHeightIndices = lambda x: int(
                round((x - self.header['minimumHeight']) * bHeight)
            )

        # High watermark encoding performed during toFile
        self.u = list(map(quantizeLonIndices, topology.uVertex))
        self.v = list(map(quantizeLatIndices, topology.vVertex))
        self.h = list(map(quantizeHeightIndices, topology.hVertex))
        self.indices = topology.indexData

        # List all the vertices on the edge of the tile
        # High water mark encoded?
        for i in range(0, len(self.indices)):
            # Use original coordinates
            indice = self.indices[i]
            lon = topology.uVertex[indice]
            lat = topology.vVertex[indice]

            if lon == self._west and indice not in self.westI:
                self.westI.append(indice)
            elif lon == self._east and indice not in self.eastI:
                self.eastI.append(indice)

            if lat == self._south and indice not in self.southI:
                self.southI.append(indice)
            elif lat == self._north and indice not in self.northI:
                self.northI.append(indice)

        self.hasLighting = topology.hasLighting
        if self.hasLighting:
            self.vLight = topology.verticesUnitVectors
