# -*- coding: utf-8 -*-
import json
import os
import platform

from future.utils import old_div

from quantized_mesh_tile import TerrainTopology
from quantized_mesh_tile.editable_terrain import EditableTerrainTile
from quantized_mesh_tile.global_geodetic import GlobalGeodetic

MAX = 32767.0


def lerp(p, q, time):
    return ((1.0 - time) * p) + (time * q)


def get_tmp_path():
    current_system = platform.system()
    if 'Windows' is current_system:
        return 'c:/Temp/'
    else:
        return '/tmp/'


def get_tile(z, x, y):
    terrain_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'data/%s_%s_%s.terrain' % (z, x, y))
    return load_tile(terrain_path, x, y, z)


def load_tile(terrain_path, x, y, z):
    """

    :rtype: EditableTerrainTile
    """
    geodetic = GlobalGeodetic(True)
    [minx, miny, maxx, maxy] = geodetic.TileBounds(x, y, z)
    tile = EditableTerrainTile(west=minx, south=miny, east=maxx, north=maxy)
    tile.fromFile(terrain_path, has_lighting=True)
    return tile


def build_terrain_tile(quantized_triangles, x, y, z, min_h=0, max_h=500, has_lightning=True):
    geodetic = GlobalGeodetic(True)
    [minx, miny, maxx, maxy] = geodetic.TileBounds(x, y, z)

    triangles = []
    for quantized_triangle in quantized_triangles:
        triangle = []
        for quantized_vertex in quantized_triangle:
            longitude = (lerp(minx, maxx, old_div(float(quantized_vertex[0]), MAX)))
            latitude = (lerp(miny, maxy, old_div(float(quantized_vertex[1]), MAX)))
            height = (lerp(min_h, max_h, old_div(float(quantized_vertex[2]), MAX)))
            triangle.append([longitude, latitude, height])
        triangles.append(triangle)

    topology = TerrainTopology(geometries=triangles, autocorrectGeometries=True, hasLighting=has_lightning)
    tile = EditableTerrainTile(west=minx, south=miny, east=maxx, north=maxy)
    tile.set_name("{}_{}_{}".format(z, x, y))
    tile.fromTerrainTopology(topology)
    return tile


def read_quantized_triangles():
    quantized_triangles_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            'data/quantizedTriangles.json')
    with open(quantized_triangles_path, mode='r') as json_file:
        data = json.load(json_file)
        quantized_triangles = data['triangles']
    return quantized_triangles
