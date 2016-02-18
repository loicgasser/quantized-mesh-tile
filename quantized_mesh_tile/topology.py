# -*- coding: utf-8 -*-

import math
import numpy as np
from osgeo import ogr
from llh_ecef import LLH2ECEF
from utils import computeNormals


class TerrainTopology(object):

    def __init__(self, features=[], hasLighting=False):

        if not isinstance(features, list):
            raise TypeError('Please provide a list of GDAL features')

        self.features = features
        self.hasLighting = hasLighting

        self.vertices = []
        self.cartesianVertices = []
        self.faces = []
        self.verticesLookup = {}

    def __str__(self):
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

    """
    The vertices represent the coordinates of a triangle in 3d. [lon/lat/height]
    """

    def addVertices(self, vertices):
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

    """
    Builds a terrain topology from a list of GDAL features.
    """

    def fromGDALFeatures(self):
        for feature in self.features:
            if not isinstance(feature, ogr.Feature):
                raise TypeError('Only GDAL features are supported')

            geometry = feature.GetGeometryRef()
            dim = geometry.GetCoordinateDimension()
            if dim != 3:
                raise TypeError('A feature with a dimension of %s has been found.' % dim)

            vertices = self._verticesFromGDALGeometry(geometry)
            self.addVertices(vertices)
        self.create()
        self.features = []

    """
    Once all the vertices have been added, create numpy arrays
    """

    def create(self):
        self.vertices = np.array(self.vertices, dtype='float')
        self.cartesianVertices = np.array(self.cartesianVertices, dtype='float')
        self.faces = np.array(self.faces, dtype='int')
        if self.hasLighting:
            self.verticesUnitVectors = computeNormals(
                self.cartesianVertices, self.faces)
        self.verticesLookup = {}

    """
    Check if the vertex has already been discovered
    and return its index (or None if not found)
    """

    def _lookupVertexIndex(self, lookupKey):
        if lookupKey in self.verticesLookup:
            return self.verticesLookup[lookupKey]

    """
    We expect a ring GDAL geometry and return a list of vertices.
    """

    def _verticesFromGDALGeometry(self, geometry):
        # 0 refers to the ring
        ring = geometry.GetGeometryRef(0)
        points = ring.GetPoints()
        # Remove last point of the polygon and keep only 3 coordinates
        vertices = points[0: len(points) - 1]
        return vertices

    """
    Inspired by:
    http://stackoverflow.com/questions/1709283/
        how-can-i-sort-a-coordinate-list-for-a-rectangle-counterclockwise
    Helper function to make sure vertices unwind in counterwise order
    """

    def _assureCounterClockWise(self, vertices):
        if len(vertices) != 3:
            raise TypeError('A ring must have exactly 3 coordinates.')

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
