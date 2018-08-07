""" This module defines the :class:`quantized_mesh_tile.topology.TerrainTopology`.

Reference
---------
"""
from __future__ import division


from builtins import object
from past.utils import old_div
import math
import numpy as np
from .llh_ecef import LLH2ECEF
from .utils import computeNormals, collapseIntoTriangles
from shapely.geometry.base import BaseGeometry
from shapely.geometry.polygon import Polygon
from shapely.wkb import loads as load_wkb
from shapely.wkt import loads as load_wkt


class TerrainTopology(object):
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

        Default is `[]`.

    ``autocorrectGeometries``

        When set to `True`, it will attempt to fix geometries that are not
        triangles. This often happens when geometries are clipped from an existing mesh.

        Default is `False`.

    ``hasLighting``

        Indicate whether unit vectors should be computed for the lighting extension.

        Default is `False`.

    Usage example::

        from quantized_mesh_tile.topology import TerrainTopology
        triangles = [
            [[7.3828125, 44.6484375, 303.3],
             [7.3828125, 45.0, 320.2],
             [7.5585937, 44.82421875, 310.2]],
            [[7.3828125, 44.6484375, 303.3],
             [7.734375, 44.6484375, 350.3],
             [7.734375, 44.6484375, 350.3]],
            [[7.734375, 44.6484375, 350.3],
             [7.734375, 45.0, 330.3],
             [7.5585937, 44.82421875, 310.2]],
            [[7.734375, 45.0, 330.3],
             [7.5585937, 44.82421875, 310.2],
             [7.3828125, 45.0, 320.2]]
        ]
        topology = TerrainTopology(geometries=triangles)
        print topology

    """

    def __init__(self, geometries=[], autocorrectGeometries=False, hasLighting=False):

        self.geometries = geometries
        self.autocorrectGeometries = autocorrectGeometries
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
        msg += '\nNumber of triangles: %s' % (old_div(len(self.indexData), 3))
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
            for geometry in geometries:
                if isinstance(geometry, (str, bytes)):
                    geometry = self._loadGeometry(geometry)
                    vertices = self._extractVertices(geometry)
                elif isinstance(geometry, BaseGeometry):
                    vertices = self._extractVertices(geometry)
                else:
                    vertices = geometry

                if self.autocorrectGeometries:
                    if len(vertices) > 3:
                        triangles = collapseIntoTriangles(vertices)
                        for triangle in triangles:
                            self._addVertices(triangle)
                    else:
                        self._addVertices(vertices)
                else:
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
        if len(vertices) != 4 and not self.autocorrectGeometries:
            raise ValueError('None triangular shape has beeen found.')
        return vertices[:len(vertices) - 1]

    def _loadGeometry(self, geometrySpec):
        """
        A private method to convert a (E)WKB or (E)WKT to a Shapely geometry.
        """
        if type(geometrySpec) is str and geometrySpec.startswith('POLYGON Z'):
            try:
                geometry = load_wkt(geometrySpec)
            except Exception:
                geometry = None
        else:
            try:
                geometry = load_wkb(geometrySpec)
            except Exception:
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
        http://stackoverflow.com/questions/1709283/\
        how-can-i-sort-a-coordinate-list-for-a-rectangle-counterclockwise
        """
        mlat = old_div(sum(coord[0] for coord in vertices), float(len(vertices)))
        mlon = old_div(sum(coord[1] for coord in vertices), float(len(vertices)))

        def algo(coord):
            return (math.atan2(coord[0] - mlat, coord[1] - mlon) + 2 * math.pi) % (
                2 * math.pi
            )
        vertices = sorted(vertices, key=algo, reverse=True)
        return vertices

    @property
    def uVertex(self):
        """
        A class property returning the horizontal coordinates of the vertices
        in the tile. Normally never used directly.
        """
        if isinstance(self.vertices, np.ndarray):
            return self.vertices[:, 0]

    @property
    def vVertex(self):
        """
        A class property returning the vertical coordinates of the vertices
        in the tile. Normally never used directly.
        """
        if isinstance(self.vertices, np.ndarray):
            return self.vertices[:, 1]

    @property
    def hVertex(self):
        """
        A class property returning the height of the vertices in the tile.
        Normally never used directly.
        """
        if isinstance(self.vertices, np.ndarray):
            return self.vertices[:, 2]

    @property
    def minLon(self):
        """
        A class property returning the minimal longitude in the tile.
        Normally never used directly.
        """
        if isinstance(self.vertices, np.ndarray):
            return np.min(self.vertices[:, 0])

    @property
    def minLat(self):
        """
        A class property returning the minimal latitude in the tile.
        Normally never used directly.
        """
        if isinstance(self.vertices, np.ndarray):
            return np.min(self.vertices[:, 1])

    @property
    def minHeight(self):
        """
        A class property returning the minimal height in the tile.
        Normally never used directly.
        """
        if isinstance(self.vertices, np.ndarray):
            return math.floor(np.min(self.vertices[:, 2]))

    @property
    def maxLon(self):
        """
        A class property returning the maximal longitude in the tile.
        Normally never used directly.
        """
        if isinstance(self.vertices, np.ndarray):
            return np.max(self.vertices[:, 0])

    @property
    def maxLat(self):
        """
        A class property returning the maximal latitude in the tile.
        Normally never used directly.
        """
        if isinstance(self.vertices, np.ndarray):
            return np.max(self.vertices[:, 1])

    @property
    def maxHeight(self):
        """
        A class property returning the maximal height in the tile.
        Normally never used directly.
        """
        if isinstance(self.vertices, np.ndarray):
            return math.ceil(np.max(self.vertices[:, 2]))

    @property
    def ecefMinX(self):
        """
        A class property returning the minimal x value in ECEF
        coordinate system. Normally never used directly.
        """
        if isinstance(self.cartesianVertices, np.ndarray):
            return np.min(self.cartesianVertices[:, 0])

    @property
    def ecefMinY(self):
        """
        A class property returning the minimal y value in ECEF
        coordinate system. Normally never used directly.
        """
        if isinstance(self.cartesianVertices, np.ndarray):
            return np.min(self.cartesianVertices[:, 1])

    @property
    def ecefMinZ(self):
        """
        A class property returning the minimal z value in ECEF
        coordinate system. Normally never used directly.
        """
        if isinstance(self.cartesianVertices, np.ndarray):
            return np.min(self.cartesianVertices[:, 2])

    @property
    def ecefMaxX(self):
        """
        A class property returning the maximal x value in ECEF
        coordinate system. Normally never used directly.
        """
        if isinstance(self.cartesianVertices, np.ndarray):
            return np.max(self.cartesianVertices[:, 0])

    @property
    def ecefMaxY(self):
        """
        A class property returning the maximal y value in ECEF
        coordinate system. Normally never used directly.
        """
        if isinstance(self.cartesianVertices, np.ndarray):
            return np.max(self.cartesianVertices[:, 1])

    @property
    def ecefMaxZ(self):
        """
        A class property returning the maximal z value in ECEF
        coordinate system. Normally never used directly.
        """
        if isinstance(self.cartesianVertices, np.ndarray):
            return np.max(self.cartesianVertices[:, 2])

    @property
    def indexData(self):
        """
        A class property retuning a list specifying how the vertices are linked together.
        These indices refer to the values in `uVertex`, `vVertex` and `hVertex` of
        this class. Normally never used directly.
        """
        if isinstance(self.faces, np.ndarray):
            return self.faces.flatten()
