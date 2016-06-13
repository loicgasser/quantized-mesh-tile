""" This module defines the :class:`quantized_mesh_tile.topology.TerrainTopology`.

Reference
---------
"""


import math
import numpy as np
from llh_ecef import LLH2ECEF
from utils import computeNormals
from shapely.geometry.base import BaseGeometry
from shapely.geometry.polygon import Polygon
from shapely.wkb import loads as load_wkb
from shapely.wkt import loads as load_wkt


class TerrainTopology:
    """
    This class is used to build the terrain tile topology.

    Contructor arguments:

    ``geometries``

        A list of shapely polygon geometries representing 3 dimensional triangles.
        or
        A list of WKT or WKB Polygons representing 3 dimensional triangles.
        or
        A list of triplet of vertices using the following structure:
        ``(((lon0/lat0/height0),(...),(lon2,lat2,height2)),(...))``

        Default is ``[]``.

    ``hasLighting``

        Indicate whether unit vectors should be computed for the lighting extension.

        Default is ``False``.

    """

    def __init__(self, geometries=[], hasLighting=False):

        self.geometries = geometries
        self.hasLighting = hasLighting

        self.vertices = []
        self.cartesianVertices = []
        self.faces = []
        self.verticesLookup = {}

        if len(self.geometries) > 0:
            self.addGeometries(self.geometries)

    def __repr__(self):
        msg = 'Min height:'
        msg += '\n%s' % self.minHeight
        msg += '\nMax height:'
        msg += '\n%s' % self.maxHeight
        msg += '\nuVertex length:'
        msg += '\n%s' % len(self.uVertex)
        msg += '\nuVertex list:'
        msg += '\n%s' % self.uVertex
        msg += '\nvVertex length:'
        msg += '\n%s' % len(self.vVertex)
        msg += '\nuVertex list:'
        msg += '\n%s' % self.vVertex
        msg += '\nhVertex length:'
        msg += '\n%s' % len(self.hVertex)
        msg += '\nhVertex list:'
        msg += '\n%s' % self.hVertex
        msg += '\nindexData length:'
        msg += '\n%s' % len(self.indexData)
        msg += '\nindexData list:'
        msg += '\n%s' % self.indexData
        msg += '\nNumber of triangles: %s' % (len(self.indexData) / 3)
        return msg

    def addGeometries(self, geometries):
        """
        Method to add geometries to the terrain tile topology.

        Arguments:

        ``geometries``

            A list of shapely polygon geometries representing 3 dimensional triangles.
            or
            A list of WKT or WKB Polygons representing 3 dimensional triangles.
            or
            A list of triplet of vertices using the following structure:
            ``(((lon0/lat0/height0),(...),(lon2,lat2,height2)),(...))``
        """
        if isinstance(geometries, (list, tuple)) and len(geometries) > 0:
            isVerticesList = self._isVerticesList(geometries)
            for geometry in geometries:
                if not isVerticesList:
                    if not isinstance(geometry, BaseGeometry):
                        geometry = self._loadGeometry(geometry)
                    vertices = self._extractVertices(geometry)
                else:
                    vertices = geometry
                self._addVertices(vertices)
            self._create()

    def _extractVertices(self, geometry):
        """
        Method to extract the triangle vertices from a Shapely geometry.
        ``((lon0/lat0/height0),(...),(lon2,lat2,height2))``

        You should normally never use this method directly.
        """
        if not geometry.has_z:
            raise ValueError('Missing z dimension.')
        if not isinstance(geometry, Polygon):
            raise ValueError('Only polygons are accepted.')
        vertices = list(geometry.exterior.coords)
        if len(vertices) != 4:
            raise ValueError('None triangular shape has beeen found.')
        return vertices[:3]

    def _isVerticesList(self, geometries):
        """
        Method to determine if the geometries provided are in the form of
        a list of vertices.

        You should normally never use this method directly.
        """
        geom = geometries[0]
        if len(geom) == 3:
            coords = geom[0]
            if len(coords) == 3:
                return True
        else:
            return False

    def _loadGeometry(self, geometrySpec):
        """
        A private method to convert a (E)WKB or (E)WKT to a Shapely geometry.
        """
        try:
            geometry = load_wkb(geometrySpec)
        except:
            try:
                geometry = load_wkt(geometrySpec)
            except:
                geometry = None

        if geometry is None:
            raise ValueError('Failed to convert WKT or WKB to a Shapely geometry')

        return geometry

    def _addVertices(self, vertices):
        """
        A private method to add vertices to the terrain tile topology.
        """
        vertices = self._assureCounterClockWise(vertices)
        face = []
        for vertex in vertices:
            lookupKey = ','.join(
                ["{:.14f}".format(vertex[0]),
                 "{:.14f}".format(vertex[1]),
                 "{:.14f}".format(vertex[2])]
            )
            faceIndex = self._lookupVertexIndex(lookupKey)
            if faceIndex is not None:
                # Sometimes we can have triangles with zero area
                # (due to unfortunate clipping)
                # In that case skip them
                # if faceIndex in face:
                #    break
                face.append(faceIndex)
            else:
                self.vertices.append(vertex)
                self.cartesianVertices.append(
                    LLH2ECEF(vertex[0], vertex[1], vertex[2]))
                faceIndex = len(self.vertices) - 1
                self.verticesLookup[lookupKey] = faceIndex
                face.append(faceIndex)
        # if len(face) == 3:
        self.faces.append(face)

    def _create(self):
        """
        A private method to create the final terrain data structure.
        """
        self.vertices = np.array(self.vertices, dtype='float')
        self.cartesianVertices = np.array(self.cartesianVertices, dtype='float')
        self.faces = np.array(self.faces, dtype='int')
        if self.hasLighting:
            self.verticesUnitVectors = computeNormals(
                self.cartesianVertices, self.faces)
        self.verticesLookup = {}

    def _lookupVertexIndex(self, lookupKey):
        """
        A private method to determine if the vertex has already been discovered
        and return its index (or None if not found).
        """
        if lookupKey in self.verticesLookup:
            return self.verticesLookup[lookupKey]

    def _assureCounterClockWise(self, vertices):
        """
        Private method to make sure vertices unwind in counterwise order.
        Inspired by:
        http://stackoverflow.com/questions/1709283/
            how-can-i-sort-a-coordinate-list-for-a-rectangle-counterclockwise
        """
        mlat = sum(coord[0] for coord in vertices) / float(len(vertices))
        mlon = sum(coord[1] for coord in vertices) / float(len(vertices))

        def algo(coord):
            return (math.atan2(coord[0] - mlat, coord[1] - mlon) + 2 * math.pi) % (
                2 * math.pi
            )

        vertices.sort(key=algo, reverse=True)
        return vertices

    @property
    def uVertex(self):
        if isinstance(self.vertices, np.ndarray):
            return self.vertices[:, 0]

    @property
    def vVertex(self):
        if isinstance(self.vertices, np.ndarray):
            return self.vertices[:, 1]

    @property
    def hVertex(self):
        if isinstance(self.vertices, np.ndarray):
            return self.vertices[:, 2]

    @property
    def minLon(self):
        if isinstance(self.vertices, np.ndarray):
            return np.min(self.vertices[:, 0])

    @property
    def minLat(self):
        if isinstance(self.vertices, np.ndarray):
            return np.min(self.vertices[:, 1])

    @property
    def minHeight(self):
        if isinstance(self.vertices, np.ndarray):
            return np.min(self.vertices[:, 2])

    @property
    def maxLon(self):
        if isinstance(self.vertices, np.ndarray):
            return np.max(self.vertices[:, 0])

    @property
    def maxLat(self):
        if isinstance(self.vertices, np.ndarray):
            return np.max(self.vertices[:, 1])

    @property
    def maxHeight(self):
        if isinstance(self.vertices, np.ndarray):
            return np.max(self.vertices[:, 2])

    @property
    def ecefMinX(self):
        if isinstance(self.cartesianVertices, np.ndarray):
            return np.min(self.cartesianVertices[:, 0])

    @property
    def ecefMinY(self):
        if isinstance(self.cartesianVertices, np.ndarray):
            return np.min(self.cartesianVertices[:, 1])

    @property
    def ecefMinZ(self):
        if isinstance(self.cartesianVertices, np.ndarray):
            return np.min(self.cartesianVertices[:, 2])

    @property
    def ecefMaxX(self):
        if isinstance(self.cartesianVertices, np.ndarray):
            return np.max(self.cartesianVertices[:, 0])

    @property
    def ecefMaxY(self):
        if isinstance(self.cartesianVertices, np.ndarray):
            return np.max(self.cartesianVertices[:, 1])

    @property
    def ecefMaxZ(self):
        if isinstance(self.cartesianVertices, np.ndarray):
            return np.max(self.cartesianVertices[:, 2])

    @property
    def indexData(self):
        if isinstance(self.faces, np.ndarray):
            return self.faces.flatten()
