# -*- coding: utf-8 -*-

import math

# Constants taken from http://cesiumjs.org/2013/04/25/Horizon-culling/
radiusX = 6378137.0
radiusY = 6378137.0
radiusZ = 6356752.3142451793

# Stolen from https://github.com/bistromath/gr-air-modes/blob/master/python/mlat.py
# WGS84 reference ellipsoid constants
# http://en.wikipedia.org/wiki/Geodetic_datum#Conversion_calculations
# http://en.wikipedia.org/wiki/File%3aECEF.png
wgs84_a = radiusX  # Semi-major axis
wgs84_b = radiusZ  # Semi-minor axis
wgs84_e2 = 0.0066943799901975848  # First eccentricity squared
wgs84_a2 = wgs84_a**2  # To speed things up a bit
wgs84_b2 = wgs84_b**2


_DEG2RAD = math.pi / 180.0
_sin = math.sin
_cos = math.cos
_sqrt = math.sqrt


def LLH2ECEF(lon, lat, alt):
    lat_r = lat * _DEG2RAD
    lon_r = lon * _DEG2RAD

    sin_lat = _sin(lat_r)
    cos_lat = _cos(lat_r)
    n_val = wgs84_a / _sqrt(1.0 - wgs84_e2 * sin_lat * sin_lat)

    nalt = n_val + alt
    x = nalt * cos_lat * _cos(lon_r)
    y = nalt * cos_lat * _sin(lon_r)
    z = (n_val * (1.0 - wgs84_e2) + alt) * sin_lat

    return [x, y, z]


# alt is in meters


def ECEF2LLH(x, y, z):
    ep = math.sqrt((wgs84_a2 - wgs84_b2) / wgs84_b2)
    p = math.sqrt(x**2 + y**2)
    th = math.atan2(wgs84_a * z, wgs84_b * p)
    lon = math.atan2(y, x)
    lat = math.atan2(
        z + ep**2 * wgs84_b * math.sin(th) ** 3,
        p - wgs84_e2 * wgs84_a * math.cos(th) ** 3,
    )
    N = wgs84_a / math.sqrt(1 - wgs84_e2 * math.sin(lat) ** 2)
    alt = p / math.cos(lat) - N

    r = 180 / math.pi
    lon *= r
    lat *= r

    return [lon, lat, alt]
