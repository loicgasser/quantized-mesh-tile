"""This module defines the :class:`quantized_mesh_tile.terrain.TerrainTile`.
More information about the format specification can be found here:
https://github.com/AnalyticalGraphicsInc/quantized-mesh

Reference
---------
"""

import gzip
import io
import os
import struct
import warnings
from collections import OrderedDict

import numpy as np

from quantized_mesh_tile.exceptions import TerrainTileError

from . import horizon_occlusion_point as occ
from .bbsphere import BoundingSphere
from .topology import TerrainTopology
from .utils import (
    decodeIndices,
    encodeIndices,
    gzipFileObject,
    octDecode,
    octEncode,
    packEntry,
    packIndices,
    ungzipFileObject,
    unpackEntry,
    zigZagDecode,
    zigZagEncode,
)

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

    quantizedMeshHeader = OrderedDict(
        [
            ["centerX", "d"],  # 8bytes
            ["centerY", "d"],
            ["centerZ", "d"],
            ["minimumHeight", "f"],  # 4bytes
            ["maximumHeight", "f"],
            ["boundingSphereCenterX", "d"],
            ["boundingSphereCenterY", "d"],
            ["boundingSphereCenterZ", "d"],
            ["boundingSphereRadius", "d"],
            ["horizonOcclusionPointX", "d"],
            ["horizonOcclusionPointY", "d"],
            ["horizonOcclusionPointZ", "d"],
        ]
    )

    vertexData = OrderedDict(
        [
            # 4bytes -> determines the size of the 3 following arrays
            ["vertexCount", "I"],
            ["uVertexCount", "H"],  # 2bytes, unsigned short
            ["vVertexCount", "H"],
            ["heightVertexCount", "H"],
        ]
    )

    indexData16 = OrderedDict([["triangleCount", "I"], ["indices", "H"]])
    indexData32 = OrderedDict([["triangleCount", "I"], ["indices", "I"]])

    EdgeIndices16 = OrderedDict(
        [
            ["westVertexCount", "I"],
            ["westIndices", "H"],
            ["southVertexCount", "I"],
            ["southIndices", "H"],
            ["eastVertexCount", "I"],
            ["eastIndices", "H"],
            ["northVertexCount", "I"],
            ["northIndices", "H"],
        ]
    )
    EdgeIndices32 = OrderedDict(
        [
            ["westVertexCount", "I"],
            ["westIndices", "I"],
            ["southVertexCount", "I"],
            ["southIndices", "I"],
            ["eastVertexCount", "I"],
            ["eastIndices", "I"],
            ["northVertexCount", "I"],
            ["northIndices", "I"],
        ]
    )

    ExtensionHeader = OrderedDict([["extensionId", "B"], ["extensionLength", "I"]])

    OctEncodedVertexNormals = OrderedDict([["xy", "B"]])

    WaterMask = OrderedDict([["xy", "B"]])

    # 16 bits  = 2^16
    BYTESPLIT = 65536

    # min and max quantized values for indices
    MIN = 0.0
    MAX = 32767.0

    # Coordinates are given in lon/lat WSG84
    def __init__(self, *_, **kwargs):
        self._west = kwargs.get("west", -1.0)
        self._east = kwargs.get("east", 1.0)
        self._south = kwargs.get("south", -1.0)
        self._north = kwargs.get("north", 1.0)
        self._longs = []
        self._lats = []
        self._heights = []
        self._triangles = []
        self._workingUnitLongitude = None
        self._workingUnitLatitude = None
        self._deltaHeight = None
        self.EPSG = 4326

        # Extensions
        self.vLight = []
        self.watermask = kwargs.get("watermask", [])
        self.hasWatermask = kwargs.get("hasWatermask", bool(self.watermask))

        self.header = OrderedDict()
        for k in TerrainTile.quantizedMeshHeader.keys():
            self.header[k] = 0.0
        self.u = []
        self.v = []
        self.h = []
        self.indices = []
        self.westI = []
        self.southI = []
        self.eastI = []
        self.northI = []

        topology = kwargs.get("topology")
        if topology is not None:
            self.fromTerrainTopology(topology)

    def __repr__(self):
        msg = "Header: %s\n" % self.header
        # Output intermediate structure
        msg += "\nVertexCount: %s" % len(self.u)
        msg += "\nuVertex: %s" % self.u
        msg += "\nvVertex: %s" % self.v
        msg += "\nhVertex: %s" % self.h
        msg += "\nindexDataCount: %s" % len(self.indices)
        msg += "\nindexData: %s" % self.indices
        msg += "\nwestIndicesCount: %s" % len(self.westI)
        msg += "\nwestIndices: %s" % self.westI
        msg += "\nsouthIndicesCount: %s" % len(self.southI)
        msg += "\nsouthIndices: %s" % self.southI
        msg += "\neastIndicesCount: %s" % len(self.eastI)
        msg += "\neastIndices: %s" % self.eastI
        msg += "\nnorthIndicesCount: %s" % len(self.northI)
        msg += "\nnorthIndices: %s\n" % self.northI
        # Output coordinates
        msg += "\nNumber of triangles: %s" % (len(self.indices) // 3)
        msg += "\nTriangles coordinates in EPSG %s" % self.EPSG
        msg += "\n%s" % self.getTrianglesCoordinates()

        return msg

    @property
    def bounds(self):
        return [self._west, self._south, self._east, self._north]

    def getContentType(self):
        """
        A method to determine the content type of a tile.
        """
        baseContent = "application/vnd.quantized-mesh"
        if self.hasLighting and self.hasWatermask:
            return baseContent + ";extensions=octvertexnormals-watermask"
        elif self.hasLighting:
            return baseContent + ";extensions=octvertexnormals"
        elif self.hasWatermask:
            return baseContent + ";extensions=watermask"
        else:
            return baseContent

    def getVerticesCoordinates(self):
        """
        A method to retrieve the coordinates of the vertices in lon,lat,height.
        """
        self._computeVerticesCoordinates()
        return [
            (lon, lat, height)
            for lon, lat, height in zip(self._longs, self._lats, self._heights)
        ]

    def getTrianglesCoordinates(self):
        """
        A method to retrieve triplet of coordinates representing the triangles
        in lon,lat,height.
        """
        self._computeVerticesCoordinates()
        triangles = []
        nbTriangles = len(self.indices)
        if nbTriangles % 3 != 0:
            raise TerrainTileError("Corrupted tile")
        for i in range(0, nbTriangles - 1, 3):
            vi1 = self.indices[i]
            vi2 = self.indices[i + 1]
            vi3 = self.indices[i + 2]
            triangle = (
                (self._longs[vi1], self._lats[vi1], self._heights[vi1]),
                (self._longs[vi2], self._lats[vi2], self._heights[vi2]),
                (self._longs[vi3], self._lats[vi3], self._heights[vi3]),
            )
            triangles.append(triangle)
        return triangles

    def _computeVerticesCoordinates(self):
        """
        A private method to compute the vertices coordinates.
        """
        if not self._longs:
            for u in self.u:
                self._longs.append(lerp(self._west, self._east, u / self.MAX))
            for v in self.v:
                self._lats.append(lerp(self._south, self._north, v / self.MAX))
            for h in self.h:
                self._heights.append(
                    lerp(
                        self.header["minimumHeight"],
                        self.header["maximumHeight"],
                        h / self.MAX,
                    )
                )

    def fromBytesIO(self, f, hasLighting=False, hasWatermask=False):
        """
        A method to read a terrain tile content.

        Arguments:

        ``f``

            An instance of io.BytesIO containing the terrain data. (Required)

        ``hasLighting``

            Indicate if the tile contains lighting information. Default is ``False``.

        ``hasWatermask``

            Indicate if the tile contains watermask information. Default is ``False``.

        Note:
            Only extension IDs 1 (Oct-Encoded Per-Vertex Normals) and 2 (Water Mask)
            are supported. If the tile contains other extensions (e.g., Metadata),
            they will be skipped and a warning will be issued.
        """
        # pylint: disable=attribute-defined-outside-init
        self.hasLighting = hasLighting
        self.hasWatermask = hasWatermask

        # Header - batch read all 12 values: 3d 2f 4d 3d = 88 bytes
        header_data = f.read(88)
        header_values = struct.unpack('<3d2f4d3d', header_data)
        for i, k in enumerate(TerrainTile.quantizedMeshHeader):
            self.header[k] = header_values[i]

        # Vertices
        vertexCount = struct.unpack('<I', f.read(4))[0]

        # Bulk read vertex arrays
        is16bit = vertexCount <= TerrainTile.BYTESPLIT
        v_dtype = np.uint16 if is16bit else np.uint32
        v_bytes = vertexCount * (2 if is16bit else 4)

        u_raw = np.frombuffer(f.read(v_bytes), dtype=v_dtype).astype(np.int32)
        v_raw = np.frombuffer(f.read(v_bytes), dtype=v_dtype).astype(np.int32)
        h_raw = np.frombuffer(f.read(v_bytes), dtype=v_dtype).astype(np.int32)

        # Vectorized zigzag decode: (z >> 1) ^ (-(z & 1))
        u_decoded = (u_raw >> 1) ^ (-(u_raw & 1))
        v_decoded = (v_raw >> 1) ^ (-(v_raw & 1))
        h_decoded = (h_raw >> 1) ^ (-(h_raw & 1))

        # Delta decode via cumulative sum
        self.u = np.cumsum(u_decoded).tolist()
        self.v = np.cumsum(v_decoded).tolist()
        self.h = np.cumsum(h_decoded).tolist()

        # Indices - bulk read
        idx_type = 'H' if is16bit else 'I'
        idx_dtype = np.uint16 if is16bit else np.uint32
        idx_bytes = 2 if is16bit else 4

        triangleCount = struct.unpack('<I', f.read(4))[0]
        n_indices = triangleCount * 3
        ind_raw = np.frombuffer(f.read(n_indices * idx_bytes), dtype=idx_dtype)
        self.indices = decodeIndices(ind_raw.tolist())

        # Edges - bulk read each edge
        def _readEdge():
            count = struct.unpack('<I', f.read(4))[0]
            if count == 0:
                return []
            data = f.read(count * idx_bytes)
            return list(struct.unpack(f'<{count}{idx_type}', data))

        self.westI = _readEdge()
        self.southI = _readEdge()
        self.eastI = _readEdge()
        self.northI = _readEdge()

        if self.hasLighting:
            # Light extension header
            extensionId, extensionLength = struct.unpack('<BI', f.read(5))
            if extensionId == 1:
                light_data = np.frombuffer(f.read(extensionLength), dtype=np.uint8)
                self.vLight = [
                    octDecode(int(light_data[i * 2]), int(light_data[i * 2 + 1]))
                    for i in range(extensionLength // 2)
                ]

        if self.hasWatermask:
            extensionId, extensionLength = struct.unpack('<BI', f.read(5))
            if extensionId == 2:
                mask_data = np.frombuffer(f.read(extensionLength), dtype=np.uint8)
                if extensionLength > 1:
                    self.watermask = mask_data.reshape(256, 256).tolist()
                else:
                    self.watermask = [mask_data.tolist()]

        # Check for unsupported extensions and skip them with a warning
        self._skipUnsupportedExtensions(f)

    def _skipUnsupportedExtensions(self, f):
        """Skip any unsupported extensions at the end of the file with warnings.

        Only extension IDs 1 (Oct-Encoded Per-Vertex Normals) and 2 (Water Mask)
        are supported. Extensions 3+ (e.g., Metadata) will be skipped with a warning.
        """
        meta = TerrainTile.ExtensionHeader
        while True:
            data = f.read(1)
            if not data:
                # Reached end of file
                break

            # Put the byte back and try to read extension header
            f.seek(f.tell() - 1)
            try:
                extensionId = unpackEntry(f, meta["extensionId"])
                extensionLength = unpackEntry(f, meta["extensionLength"])

                # Supported extension IDs: 1=Oct-Encoded Per-Vertex Normals, 2=Water Mask
                # Unsupported: 3=Metadata, 4+=unknown
                warnings.warn(
                    f"Skipping unsupported terrain tile extension "
                    f"(id={extensionId}, length={extensionLength} bytes). "
                    f"Only extensions 1 (lighting) and 2 (watermask) are supported.",
                    UserWarning,
                    stacklevel=3,
                )
                # Skip the extension data
                f.read(extensionLength)
            except struct.error:
                # Could not parse as extension header, stop
                break

    @staticmethod
    def _iterUnpackAndDecodeVertices(f, vertexCount, structType):
        """
        A private method to itertatively unpack and decode indices.
        """
        i = 0
        # Delta decoding
        delta = 0
        while i != vertexCount:
            delta += zigZagDecode(unpackEntry(f, structType))
            yield delta
            i += 1

    @staticmethod
    def _iterUnpackIndices(f, indicesCount, structType):
        """
        A private method to iteratively unpack indices
        """
        i = 0
        while i != indicesCount:
            yield unpackEntry(f, structType)
            i += 1

    @staticmethod
    def _iterUnpackAndDecodeLight(f, extensionLength, structType):
        """
        A private method to iteratively unpack light vector.
        """
        i = 0
        xyCount = extensionLength / 2
        while i != xyCount:
            yield octDecode(unpackEntry(f, structType), unpackEntry(f, structType))
            i += 1

    @staticmethod
    def _iterUnpackWatermaskRow(f, extensionLength, structType):
        """
        A private method to iteratively unpack watermask rows
        """
        i = 0
        xyCount = 0
        row = []
        while xyCount != extensionLength:
            row.append(unpackEntry(f, structType))
            if i == 255:
                yield row
                i = 0
                row = []
            else:
                i += 1
            xyCount += 1
        if row:
            yield row

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
        with open(filePath, "rb") as f:
            if gzipped:
                f = ungzipFileObject(f)
            self.fromBytesIO(f, hasLighting=hasLighting, hasWatermask=hasWatermask)

    def toBytesIO(self, gzipped=False):
        """
        A method to write the terrain tile data to a file-like object (a string buffer).

        Arguments:

        ``gzipped``

            Indicate if the content should be gzipped. Default is ``False``.
        """
        f = io.BytesIO()
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
            raise IOError("File %s already exists" % filePath)

        if not gzipped:
            with open(filePath, "wb") as f:
                self._writeTo(f)
        else:
            with gzip.open(filePath, "wb") as f:
                self._writeTo(f)

    def _getWorkingUnitLatitude(self):
        if not self._workingUnitLatitude:
            self._workingUnitLatitude = self.MAX / (self._north - self._south)
        return self._workingUnitLatitude

    def _getWorkingUnitLongitude(self):
        if not self._workingUnitLongitude:
            self._workingUnitLongitude = self.MAX / (self._east - self._west)
        return self._workingUnitLongitude

    def _getDeltaHeight(self):
        if not self._deltaHeight:
            maxHeight = self.header["maximumHeight"]
            minHeight = self.header["minimumHeight"]
            self._deltaHeight = maxHeight - minHeight
        return self._deltaHeight

    def _dequantizeHeight(self, h):
        """
        Private helper method to convert quantized tile (h) values to real world height
        values
        :param h: the quantized height value
        :return: the height in ground units (meter)
        """
        return lerp(
            self.header["minimumHeight"], self.header["maximumHeight"], h / self.MAX
        )

    def _writeTo(self, f):
        """
        A private method to write the terrain tile to a file or file-like object.
        """
        write = f.write

        # Header - batch pack all 12 values at once
        header_values = [self.header[k] for k in TerrainTile.quantizedMeshHeader]
        write(struct.pack('<3d2f4d3d', *header_values))

        # Delta decoding
        vertexCount = len(self.u)
        # Vertices
        write(struct.pack('<I', vertexCount))

        # Pre-compute all deltas using numpy diff
        u_arr = np.array(self.u, dtype=np.int32)
        v_arr = np.array(self.v, dtype=np.int32)
        h_arr = np.array(self.h, dtype=np.int32)

        u_deltas = np.empty(len(u_arr), dtype=np.int32)
        v_deltas = np.empty(len(v_arr), dtype=np.int32)
        h_deltas = np.empty(len(h_arr), dtype=np.int32)
        u_deltas[0] = u_arr[0]
        v_deltas[0] = v_arr[0]
        h_deltas[0] = h_arr[0]
        if len(u_arr) > 1:
            u_deltas[1:] = np.diff(u_arr)
            v_deltas[1:] = np.diff(v_arr)
            h_deltas[1:] = np.diff(h_arr)

        # Vectorized zigzag encode: (n << 1) ^ (n >> 31)
        u_encoded = ((u_deltas << 1) ^ (u_deltas >> 31)).astype(np.uint16)
        v_encoded = ((v_deltas << 1) ^ (v_deltas >> 31)).astype(np.uint16)
        h_encoded = ((h_deltas << 1) ^ (h_deltas >> 31)).astype(np.uint16)

        # Batch write all vertex data
        write(u_encoded.tobytes())
        write(v_encoded.tobytes())
        write(h_encoded.tobytes())

        # Indices
        idx_type = 'H' if vertexCount <= TerrainTile.BYTESPLIT else 'I'
        idx_dtype = np.uint16 if vertexCount <= TerrainTile.BYTESPLIT else np.uint32

        write(struct.pack('<I', len(self.indices) // 3))
        ind = encodeIndices(self.indices)
        ind_arr = np.array(ind, dtype=idx_dtype)
        write(ind_arr.tobytes())

        # Edge indices - batch pack each edge
        edge_fmt = '<I' + ('%d%s' % (len(self.westI), idx_type))
        write(struct.pack(edge_fmt, len(self.westI), *self.westI))

        edge_fmt = '<I' + ('%d%s' % (len(self.southI), idx_type))
        write(struct.pack(edge_fmt, len(self.southI), *self.southI))

        edge_fmt = '<I' + ('%d%s' % (len(self.eastI), idx_type))
        write(struct.pack(edge_fmt, len(self.eastI), *self.eastI))

        edge_fmt = '<I' + ('%d%s' % (len(self.northI), idx_type))
        write(struct.pack(edge_fmt, len(self.northI), *self.northI))

        # Extension header for light
        if len(self.vLight) > 0:
            # pylint: disable=attribute-defined-outside-init
            self.hasLighting = True
            # Extension ID=1, length=2*vertexCount
            write(struct.pack('<BI', 1, 2 * vertexCount))
            # Batch oct-encode all normals and write at once
            light_bytes = bytearray(2 * vertexCount)
            for i in range(vertexCount):
                x, y = octEncode(self.vLight[i])
                light_bytes[i * 2] = x
                light_bytes[i * 2 + 1] = y
            write(bytes(light_bytes))

        if self.watermask:
            self.hasWatermask = True
            nbRows = len(self.watermask)
            if nbRows > 1:
                write(struct.pack('<BI', 2, TILEPXS))
                if nbRows != 256:
                    raise TerrainTileError(
                        "Unexpected number of rows for the watermask: %s" % nbRows
                    )
                mask_bytes = bytearray(TILEPXS)
                offset = 0
                for i in range(nbRows):
                    row = self.watermask[i]
                    if len(row) != 256:
                        raise TerrainTileError(
                            "Unexpected number of columns for the watermask: %s" % len(row)
                        )
                    for y in row:
                        mask_bytes[offset] = int(y)
                        offset += 1
                write(bytes(mask_bytes))
            else:
                write(struct.pack('<BI', 2, 1))
                val = self.watermask[0][0]
                write(struct.pack('<B', int(val) if val is not None else 0))

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
            raise TerrainTileError(
                "topology object must be an instance of TerrainTopology"
            )

        # If the bounds are not provided use
        # topology extent instead
        if bounds is not None:
            self._west = bounds[0]
            self._east = bounds[2]
            self._south = bounds[1]
            self._north = bounds[3]
        elif set([self._west, self._south, self._east, self._north]).difference(
            set([-1.0, -1.0, 1.0, 1.0])
        ):
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

        # Center of the bounding box 3d
        centerCoords = [
            ecefMinX + (ecefMaxX - ecefMinX) * 0.5,
            ecefMinY + (ecefMaxY - ecefMinY) * 0.5,
            ecefMinZ + (ecefMaxZ - ecefMinZ) * 0.5,
        ]

        occlusionPCoords = occ.fromPoints(topology.cartesianVertices, bSphere)

        for k in TerrainTile.quantizedMeshHeader.keys():
            if k == "centerX":
                self.header[k] = centerCoords[0]
            elif k == "centerY":
                self.header[k] = centerCoords[1]
            elif k == "centerZ":
                self.header[k] = centerCoords[2]
            elif k == "minimumHeight":
                self.header[k] = topology.minHeight
            elif k == "maximumHeight":
                self.header[k] = topology.maxHeight
            elif k == "boundingSphereCenterX":
                self.header[k] = bSphere.center[0]
            elif k == "boundingSphereCenterY":
                self.header[k] = bSphere.center[1]
            elif k == "boundingSphereCenterZ":
                self.header[k] = bSphere.center[2]
            elif k == "boundingSphereRadius":
                self.header[k] = bSphere.radius
            elif k == "horizonOcclusionPointX":
                self.header[k] = occlusionPCoords[0]
            elif k == "horizonOcclusionPointY":
                self.header[k] = occlusionPCoords[1]
            elif k == "horizonOcclusionPointZ":
                self.header[k] = occlusionPCoords[2]

        # High watermark encoding performed during toFile
        # Vectorized quantization using numpy
        u_arr = np.asarray(topology.uVertex)
        v_arr = np.asarray(topology.vVertex)
        h_arr = np.asarray(topology.hVertex)

        self.u = np.round(
            (u_arr - self._west) * self._getWorkingUnitLongitude()
        ).astype(int).tolist()
        self.v = np.round(
            (v_arr - self._south) * self._getWorkingUnitLatitude()
        ).astype(int).tolist()

        deniv = self._getDeltaHeight()
        if deniv == 0:
            self.h = [0] * len(h_arr)
        else:
            self.h = np.round(
                (h_arr - self.header["minimumHeight"]) * (self.MAX / deniv)
            ).astype(int).tolist()

        self.indices = topology.indexData

        # List all the vertices on the edge of the tile
        # Use quantized values to determine if an indice belong to a tile edge
        # Use dicts for O(1) lookup while preserving insertion order (Python 3.7+)
        westI_seen = {}
        eastI_seen = {}
        southI_seen = {}
        northI_seen = {}

        for indice in self.indices:
            x = self.u[indice]
            y = self.v[indice]

            if x == self.MIN:
                westI_seen[indice] = None
            elif x == self.MAX:
                eastI_seen[indice] = None

            if y == self.MIN:
                southI_seen[indice] = None
            elif y == self.MAX:
                northI_seen[indice] = None

        self.westI = list(westI_seen)
        self.eastI = list(eastI_seen)
        self.southI = list(southI_seen)
        self.northI = list(northI_seen)

        self.hasLighting = topology.hasLighting
        if self.hasLighting:
            self.vLight = topology.verticesUnitVectors
