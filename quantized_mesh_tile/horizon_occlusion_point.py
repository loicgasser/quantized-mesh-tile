# -*- coding: utf-8 -*-

import math

from quantized_mesh_tile.exceptions import InvalidGeometryError

from . import llh_ecef as ecef

# Constants taken from http://cesiumjs.org/2013/04/25/Horizon-culling/
rX = 1.0 / ecef.radiusX
rY = 1.0 / ecef.radiusY
rZ = 1.0 / ecef.radiusZ

_sqrt = math.sqrt


# https://cesiumjs.org/2013/05/09/Computing-the-horizon-occlusion-point/
def fromPoints(points, boundingSphere):
    if len(points) < 1:
        raise InvalidGeometryError("Your list of points must contain at least 2 points")

    bc = boundingSphere.center
    sc0 = bc[0] * rX
    sc1 = bc[1] * rY
    sc2 = bc[2] * rZ

    maxMag = float('-inf')
    for pt in points:
        p0 = pt[0] * rX
        p1 = pt[1] * rY
        p2 = pt[2] * rZ

        magSq = p0*p0 + p1*p1 + p2*p2
        mag = _sqrt(magSq)
        inv = 1.0 / mag
        d0 = p0 * inv
        d1 = p1 * inv
        d2 = p2 * inv

        if magSq < 1.0:
            magSq = 1.0
        if mag < 1.0:
            mag = 1.0

        cosAlpha = d0*sc0 + d1*sc1 + d2*sc2
        # cross product magnitude
        cx = d1*sc2 - d2*sc1
        cy = d2*sc0 - d0*sc2
        cz = d0*sc1 - d1*sc0
        sinAlpha = _sqrt(cx*cx + cy*cy + cz*cz)
        cosBeta = 1.0 / mag
        sinBeta = _sqrt(magSq - 1.0) * cosBeta
        m = 1.0 / (cosAlpha * cosBeta - sinAlpha * sinBeta)
        if m > maxMag:
            maxMag = m

    return [sc0 * maxMag, sc1 * maxMag, sc2 * maxMag]
