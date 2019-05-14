# -*- coding: utf-8 -*-

from __future__ import division

import math

from past.utils import old_div

# Constants taken from http://cesiumjs.org/2013/04/25/Horizon-culling/
radiusX = 6378137.0
radiusY = 6378137.0
radiusZ = 6356752.3142451793

# Stolen from https://github.com/bistromath/gr-air-modes/blob/master/python/mlat.py
# WGS84 reference ellipsoid constants
# http://en.wikipedia.org/wiki/Geodetic_datum#Conversion_calculations
# http://en.wikipedia.org/wiki/File%3aECEF.png
wgs84_a = radiusX               # Semi-major axis
wgs84_b = radiusZ          # Semi-minor axis
wgs84_e2 = 0.0066943799901975848  # First eccentricity squared
wgs84_a2 = wgs84_a ** 2           # To speed things up a bit
wgs84_b2 = wgs84_b ** 2


def LLH2ECEF(lon, lat, alt):
    lat *= (old_div(math.pi, 180.0))
    lon *= (old_div(math.pi, 180.0))

    def n(x):
        return old_div(wgs84_a, math.sqrt(
            1 - wgs84_e2 * (math.sin(x) ** 2)))

    x = (n(lat) + alt) * math.cos(lat) * math.cos(lon)
    y = (n(lat) + alt) * math.cos(lat) * math.sin(lon)
    z = (n(lat) * (1 - wgs84_e2) + alt) * math.sin(lat)

    return [x, y, z]

# alt is in meters


def ECEF2LLH(x, y, z):
    ep = math.sqrt(old_div((wgs84_a2 - wgs84_b2), wgs84_b2))
    p = math.sqrt(x ** 2 + y ** 2)
    th = math.atan2(wgs84_a * z, wgs84_b * p)
    lon = math.atan2(y, x)
    lat = math.atan2(
        z + ep ** 2 * wgs84_b * math.sin(th) ** 3,
        p - wgs84_e2 * wgs84_a * math.cos(th) ** 3
    )
    N = old_div(wgs84_a, math.sqrt(1 - wgs84_e2 * math.sin(lat) ** 2))
    alt = old_div(p, math.cos(lat)) - N

    lon *= (old_div(180., math.pi))
    lat *= (old_div(180., math.pi))

    return [lon, lat, alt]
