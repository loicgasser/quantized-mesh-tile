# -*- coding: utf-8 -*-

import os
import cStringIO
from collections import OrderedDict
import horizon_occlusion_point as occ
from utils import (
    octEncode, octDecode, zigZagDecode, zigZagEncode,
    unpackEntry, unpackIndices, decodeIndices, packEntry, packIndices, encodeIndices
)
from bbsphere import BoundingSphere
from topology import TerrainTopology

MAX = 32767.0
# For a tile of 256px * 256px
TILEPXS = 65536


def lerp(p, q, time):
    return ((1.0 - time) * p) + (time * q)


# http://cesiumjs.org/data-and-assets/terrain/formats/quantized-mesh-1.0.html


class TerrainTile:
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
        # Reprojected coordinates
        self._easts = []
        self._norths = []
        self._alts = []
        self.targetEPSG = 4326

        # Extensions
        self.vLight = []
        self.watermask = kwargs.get('watermask', [])
        self.hasWatermask = kwargs.get('hasWatermask', bool(len(self.watermask) > 0))

        self.header = OrderedDict()
        for k, v in TerrainTile.quantizedMeshHeader.iteritems():
            self.header[k] = 0.0
        self.u = []
        self.v = []
        self.h = []
        self.indices = []
        self.westI = []
        self.southI = []
        self.eastI = []
        self.northI = []

    def __str__(self):

        msg = 'Header: %s' % self.header
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
        msg += '\nnorthIndices: %s' % self.northI
        # output coordinates
        msg += '\nCoordinates in EPSG %s ----------------------------\n' % self.targetEPSG
        msg += '\n%s' % self.getVerticesCoordinates(epsg=self.targetEPSG)

        msg += '\nNumber of triangles: %s' % (len(self.indices) / 3)
        return msg

    def getContentType(self):
        baseContent = 'application/vnd.quantized-mesh'
        if self.hasLighting and self.hasWatermask:
            return baseContent + ';extensions=octvertexnormals-watermask'
        elif self.hasLighting:
            return baseContent + ';extensions=octvertexnormals'
        elif self.hasWatermask:
            return baseContent + ';extensions=watermask'
        else:
            return baseContent

    def getVerticesCoordinates(self, epsg=4326):
        coordinates = []
        if epsg == 4326:
            if len(self._longs) == 0:
                self.computeVerticesCoordinates()
            for i, lon in enumerate(self._longs):
                coordinates.append([lon, self._lats[i], self._heights[i]])
        elif epsg != 4326:
            if len(self._easts) == 0:
                self.computeVerticesCoordinates(epsg=epsg)
            for i, east in enumerate(self._easts):
                coordinates.append([east, self._norths[i], self._alts[i]])
        return coordinates

    # This is really slow, so only do it when really needed
    def computeVerticesCoordinates(self, epsg=4326):
        if len(self._longs) == 0:
            for u in self.u:
                self._longs.append(lerp(self._west, self._east, float(u) / MAX))
            for v in self.v:
                self._lats.append(lerp(self._south, self._north, float(v) / MAX))
            for h in self.h:
                self._heights.append(
                    lerp(
                        self.header['minimumHeight'],
                        self.header['maximumHeight'],
                        float(h) / MAX
                    )
                )

    def _resetReprojectedVerticesCoordinates(self):
        self._easts = []
        self._norths = []
        self._alts = []

    def fromFile(self, filePath, west, east, south, north,
            hasLighting=False, hasWatermask=False):
        self.__init__(west=west, east=east, south=south, north=north)
        self.hasLighting = hasLighting
        self.hasWatermask = hasWatermask
        with open(filePath, 'rb') as f:
            # Header
            for k, v in TerrainTile.quantizedMeshHeader.iteritems():
                self.header[k] = unpackEntry(f, v)

            # Delta decoding
            ud = 0
            vd = 0
            hd = 0
            # Vertices
            vertexCount = unpackEntry(f, TerrainTile.vertexData['vertexCount'])
            for i in xrange(0, vertexCount):
                ud += zigZagDecode(
                    unpackEntry(f, TerrainTile.vertexData['uVertexCount'])
                )
                self.u.append(ud)
            for i in xrange(0, vertexCount):
                vd += zigZagDecode(
                    unpackEntry(f, TerrainTile.vertexData['vVertexCount'])
                )
                self.v.append(vd)
            for i in xrange(0, vertexCount):
                hd += zigZagDecode(
                    unpackEntry(f, TerrainTile.vertexData['heightVertexCount'])
                )
                self.h.append(hd)

            # Indices
            # TODO: verify padding
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

                    # Consider padding of 2 bits, no idea why?
                    f.read(2)

                    for i in xrange(0, (extensionLength / 2) - 1):
                        x = unpackEntry(f, TerrainTile.OctEncodedVertexNormals['xy'])
                        y = unpackEntry(f, TerrainTile.OctEncodedVertexNormals['xy'])
                        self.vLight.append(octDecode(x, y))

            if self.hasWatermask:
                meta = TerrainTile.ExtensionHeader
                extensionId = unpackEntry(f, meta['extensionId'])
                if extensionId == 2:
                    extensionLength = unpackEntry(f, meta['extensionLength'])
                    row = []
                    for i in xrange(0, extensionLength):
                        row.append(unpackEntry(f, TerrainTile.WaterMask['xy']))
                        if len(row) == 256:
                            self.watermask.append(row)
                            row = []
                    if len(row) > 0:
                        self.watermask.append(row)

            data = f.read(1)
            if data:
                raise Exception('Should have reached end of file, but didn\'t')

    def toStringIO(self):
        f = cStringIO.StringIO()
        self._writeTo(f)
        return f

    def toFile(self, filePath):
        if not filePath.endswith('.terrain'):
            raise Exception('Wrong file extension')

        if os.path.isfile(filePath):
            raise IOError('File %s already exists' % filePath)

        with open(filePath, 'wb') as f:
            self._writeTo(f)

    def _writeTo(self, f):
        # Header
        for k, v in TerrainTile.quantizedMeshHeader.iteritems():
            f.write(packEntry(v, self.header[k]))

        # Delta decoding
        vertexCount = len(self.u)
        # Vertices
        f.write(packEntry(TerrainTile.vertexData['vertexCount'], vertexCount))
        # Move the initial value
        f.write(
            packEntry(TerrainTile.vertexData['uVertexCount'], zigZagEncode(self.u[0]))
        )
        for i in xrange(0, vertexCount - 1):
            ud = self.u[i + 1] - self.u[i]
            f.write(packEntry(TerrainTile.vertexData['uVertexCount'], zigZagEncode(ud)))
        f.write(
            packEntry(TerrainTile.vertexData['uVertexCount'], zigZagEncode(self.v[0]))
        )
        for i in xrange(0, vertexCount - 1):
            vd = self.v[i + 1] - self.v[i]
            f.write(packEntry(TerrainTile.vertexData['vVertexCount'], zigZagEncode(vd)))
        f.write(
            packEntry(TerrainTile.vertexData['uVertexCount'], zigZagEncode(self.h[0]))
        )
        for i in xrange(0, vertexCount - 1):
            hd = self.h[i + 1] - self.h[i]
            f.write(
                packEntry(TerrainTile.vertexData['heightVertexCount'], zigZagEncode(hd))
            )

        # Indices
        # TODO: verify padding
        meta = TerrainTile.indexData16
        if vertexCount > TerrainTile.BYTESPLIT:
            meta = TerrainTile.indexData32

        f.write(packEntry(meta['triangleCount'], len(self.indices) / 3))
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
            for i in xrange(0, vertexCount - 1):
                x, y = octEncode(self.vLight[i])
                f.write(packEntry(metaV['xy'], x))
                f.write(packEntry(metaV['xy'], y))

        if len(self.watermask) > 0:
            self.hasWatermask = True
            # Extension header ID is 2 for lightening
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
                for i in xrange(0, nbRows):
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
        if not isinstance(topology, TerrainTopology):
            raise Exception('topology object must be an instance of TerrainTopology')

        # If the bounds are not provided use
        # topology extent instead
        if bounds is not None:
            self._west = bounds[0]
            self._east = bounds[2]
            self._south = bounds[1]
            self._north = bounds[3]
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

        for k, v in TerrainTile.quantizedMeshHeader.iteritems():
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

        bLon = MAX / (self._east - self._west)
        bLat = MAX / (self._north - self._south)

        quantizeLonIndices = lambda x: int(round((x - self._west) * bLon))
        quantizeLatIndices = lambda x: int(round((x - self._south) * bLat))

        deniv = self.header['maximumHeight'] - self.header['minimumHeight']
        # In case a tile is completely flat
        if deniv == 0:
            quantizeHeightIndices = lambda x: 0
        else:
            bHeight = MAX / deniv
            quantizeHeightIndices = lambda x: int(
                round((x - self.header['minimumHeight']) * bHeight)
            )

        # High watermark encoding performed during toFile
        self.u = map(quantizeLonIndices, topology.uVertex)
        self.v = map(quantizeLatIndices, topology.vVertex)
        self.h = map(quantizeHeightIndices, topology.hVertex)
        self.indices = topology.indexData

        # List all the vertices on the edge of the tile
        # High water mark encoded?
        for i in xrange(0, len(self.indices)):
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
