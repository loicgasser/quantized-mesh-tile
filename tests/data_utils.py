# -*- coding: utf-8 -*-
import json
import os
import platform

from future.utils import old_div

from quantized_mesh_tile import TerrainTopology
from quantized_mesh_tile.global_geodetic import GlobalGeodetic
from quantized_mesh_tile.terrain import lerp, TerrainTile


def getTempPath():
    currentSystem = platform.system()
    if 'Windows' is currentSystem:
        return 'c:/Temp/'
    else:
        return '/tmp/'


def getTile(z, x, y):
    terrainPath = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'data/%s_%s_%s.terrain' % (z, x, y))
    return loadTile(terrainPath, x, y, z)


def loadTile(terrainPath, x, y, z):
    """
    :rtype: EditableTerrainTile
    """
    geodetic = GlobalGeodetic(True)
    [minx, miny, maxx, maxy] = geodetic.TileBounds(x, y, z)
    tile = TerrainTile(west=minx, south=miny, east=maxx, north=maxy)
    tile.fromFile(terrainPath, hasLighting=True)
    return tile


def buildTerrainTile(quantizedTriangles, x, y, z, minH=0, maxH=500,
                     hasLightning=True):
    geodetic = GlobalGeodetic(True)
    [minX, minY, maxX, maxY] = geodetic.TileBounds(x, y, z)

    triangles = []
    for quantizedTriangle in quantizedTriangles:
        triangle = []
        for quantizedVertex in quantizedTriangle:
            longitude = (lerp(minX, maxX, old_div(float(quantizedVertex[0]),
                                                  TerrainTile.MAX)))
            latitude = (lerp(minY, maxY, old_div(float(quantizedVertex[1]),
                                                 TerrainTile.MAX)))
            height = (lerp(minH, maxH, old_div(float(quantizedVertex[2]),
                                               TerrainTile.MAX)))
            triangle.append([longitude, latitude, height])
        triangles.append(triangle)

    topology = TerrainTopology(geometries=triangles, autocorrectGeometries=True,
                               hasLighting=hasLightning)
    tile = TerrainTile(west=minX, south=minY, east=maxX, north=maxY)
    tile.setName("{}_{}_{}".format(z, x, y))
    tile.fromTerrainTopology(topology)
    return tile


def readQuantizedTriangles():
    quantizedTrianglesPath = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          'data/quantizedTriangles.json')
    with open(quantizedTrianglesPath, mode='r') as json_file:
        data = json.load(json_file)
        quantizedTriangles = data['triangles']
    return quantizedTriangles
