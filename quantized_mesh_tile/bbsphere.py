# -*- coding: utf-8 -*-

import math
from typing import List

from quantized_mesh_tile.exceptions import TerrainTileError


class BoundingSphere(object):
    def __init__(self, *_, **kwargs):
        MAX = float("infinity")
        MIN = float("-infinity")

        self.center = kwargs.get("center", [])
        self.radius = kwargs.get("radius", 0)
        self.minPointX = [MAX, MAX, MAX]
        self.minPointY = [MAX, MAX, MAX]
        self.minPointZ = [MAX, MAX, MAX]
        self.maxPointX = [MIN, MIN, MIN]
        self.maxPointY = [MIN, MIN, MIN]
        self.maxPointZ = [MIN, MIN, MIN]

    # Based on Ritter's algorithm
    def fromPoints(self, points: List):
        nbPositions = len(points)
        if nbPositions < 2:
            raise TerrainTileError("Your list of points must contain at least 2 points")

        for i in range(0, nbPositions):
            point = points[i]

            # Store the points containing the smallest and largest component
            # Used for the naive approach
            if point[0] < self.minPointX[0]:
                self.minPointX = point

            if point[1] < self.minPointY[1]:
                self.minPointY = point

            if point[2] < self.minPointZ[2]:
                self.minPointZ = point

            if point[0] > self.maxPointX[0]:
                self.maxPointX = point

            if point[1] > self.maxPointY[1]:
                self.maxPointY = point

            if point[2] > self.maxPointZ[2]:
                self.maxPointZ = point

        _sqrt = math.sqrt
        mnX = self.minPointX
        mnY = self.minPointY
        mnZ = self.minPointZ
        mxX = self.maxPointX
        mxY = self.maxPointY
        mxZ = self.maxPointZ

        # Inline magnitudeSquared(subtract(...))
        dx = mxX[0]-mnX[0]
        dy = mxX[1]-mnX[1]
        dz = mxX[2]-mnX[2]
        xSpan = dx*dx + dy*dy + dz*dz
        dx = mxY[0]-mnY[0]
        dy = mxY[1]-mnY[1]
        dz = mxY[2]-mnY[2]
        ySpan = dx*dx + dy*dy + dz*dz
        dx = mxZ[0]-mnZ[0]
        dy = mxZ[1]-mnZ[1]
        dz = mxZ[2]-mnZ[2]
        zSpan = dx*dx + dy*dy + dz*dz

        diameter1 = mnX
        diameter2 = mxX
        maxSpan = xSpan
        if ySpan > maxSpan:
            maxSpan = ySpan
            diameter1 = mnY
            diameter2 = mxY
        if zSpan > maxSpan:
            diameter1 = mnZ
            diameter2 = mxZ

        rc0 = (diameter1[0] + diameter2[0]) * 0.5
        rc1 = (diameter1[1] + diameter2[1]) * 0.5
        rc2 = (diameter1[2] + diameter2[2]) * 0.5

        dx = diameter2[0]-rc0
        dy = diameter2[1]-rc1
        dz = diameter2[2]-rc2
        radiusSquared = dx*dx + dy*dy + dz*dz
        ritterRadius = _sqrt(radiusSquared)

        # Naive center
        nc0 = (mnX[0] + mxX[0]) * 0.5
        nc1 = (mnY[1] + mxY[1]) * 0.5
        nc2 = (mnZ[2] + mxZ[2]) * 0.5
        naiveRadius = 0.0

        for i in range(nbPositions):
            p = points[i]
            p0 = p[0]
            p1 = p[1]
            p2 = p[2]

            # Naive radius
            dx = p0-nc0
            dy = p1-nc1
            dz = p2-nc2
            r = _sqrt(dx*dx + dy*dy + dz*dz)
            if r > naiveRadius:
                naiveRadius = r

            # Ritter expansion
            dx = p0-rc0
            dy = p1-rc1
            dz = p2-rc2
            octs = dx*dx + dy*dy + dz*dz
            if octs > radiusSquared:
                oct = _sqrt(octs)
                ritterRadius = (ritterRadius + oct) * 0.5
                radiusSquared = ritterRadius * ritterRadius
                otn = oct - ritterRadius
                inv = 1.0 / oct
                rc0 = (ritterRadius * rc0 + otn * p0) * inv
                rc1 = (ritterRadius * rc1 + otn * p1) * inv
                rc2 = (ritterRadius * rc2 + otn * p2) * inv

        # Keep the naive sphere if smaller
        if naiveRadius < ritterRadius:
            self.radius = ritterRadius
            self.center = [rc0, rc1, rc2]
        else:
            self.radius = naiveRadius
            self.center = [nc0, nc1, nc2]
