# -*- coding: utf-8 -*-

import math

import numpy as np

from . import cartesian3d as c3d
from . import llh_ecef as ecef

# Constants taken from http://cesiumjs.org/2013/04/25/Horizon-culling/
rX = 1.0 / ecef.radiusX
rY = 1.0 / ecef.radiusY
rZ = 1.0 / ecef.radiusZ

# Functions assumes ellipsoid scaled coordinates


def computeMagnitude(point, sphereCenter):
    magnitudeSquared = c3d.magnitudeSquared(point)
    magnitude = math.sqrt(magnitudeSquared)
    direction = c3d.multiplyByScalar(point, 1 / magnitude)

    magnitudeSquared = max(1.0, magnitudeSquared)
    magnitude = max(1.0, magnitude)

    cosAlpha = np.dot(direction, sphereCenter)
    sinAlpha = c3d.magnitude(np.cross(direction, sphereCenter))
    cosBeta = 1.0 / magnitude
    sinBeta = math.sqrt(magnitudeSquared - 1.0) * cosBeta
    return 1.0 / (cosAlpha * cosBeta - sinAlpha * sinBeta)


# https://cesiumjs.org/2013/05/09/Computing-the-horizon-occlusion-point/
def fromPoints(points, boundingSphere):

    if len(points) < 1:
        raise Exception('Your list of points must contain at least 2 points')

    # Bring coordinates to ellipsoid scaled coordinates
    def scaleDown(coord):
        return [coord[0] * rX, coord[1] * rY, coord[2] * rZ]
    scaledPoints = [scaleDown(coord) for coord in points]
    scaledSphereCenter = scaleDown(boundingSphere.center)

    def magnitude(coord):
        return computeMagnitude(coord, scaledSphereCenter)
    magnitudes = [magnitude(coord) for coord in scaledPoints]

    return c3d.multiplyByScalar(scaledSphereCenter, max(magnitudes))
