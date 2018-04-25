# -*- coding: utf-8 -*-

from __future__ import print_function

import os

from quantized_mesh_tile import TerrainTile
from quantized_mesh_tile.editable_terrain import EditableTerrainTile
from quantized_mesh_tile.topology import TerrainTopology
from operator import itemgetter
from scipy.spatial import Delaunay

from . import cartesian3d as c3d, terrain


class TileRebuilder(object):

    def __init__(self, center_tile):
        self._center = center_tile
        self._neighbours = {}

    def _get_edge_connection(self, neighbour_tile):
        center_bbox = self._center.get_bounding_box()
        neighbour_bbox = neighbour_tile.get_bounding_box()

        if center_bbox['west'] == neighbour_bbox['east']:
            return 'w'
        if center_bbox['east'] == neighbour_bbox['west']:
            return 'e'
        if center_bbox['north'] == neighbour_bbox['south']:
            return 'n'
        if center_bbox['south'] == neighbour_bbox['north']:
            return 's'
        return None

    def add_neighbour(self, neighbour_tile):
        edge_connection = self._get_edge_connection(neighbour_tile)
        self._neighbours[edge_connection] = neighbour_tile

    def rebuild_to(self, path):
        points = []
        points2d = []
        heights = []
        for edge_info, neighbour_tile in self._neighbours.items():
            points.extend(neighbour_tile.get_edge_coordinates(edge_info))

        points.extend(self._center.getVerticesCoordinates())

        for p in points:
            points2d.append([p[0], p[1]])
            heights.append(p[2])

        tri = Delaunay(points2d)
        triangles3d = []
        triangles2d = tri.simplices
        with open("{0}.points".format(path), mode='w') as debug:

            for triangle in triangles2d:
                v1 = [points2d[triangle[0]][0], points2d[triangle[0]][1], heights[triangle[0]]]
                v2 = [points2d[triangle[1]][0], points2d[triangle[1]][1], heights[triangle[1]]]
                v3 = [points2d[triangle[2]][0], points2d[triangle[2]][1], heights[triangle[2]]]

                dv1 = "{0} {1} {2}".format(points2d[triangle[0]][0], points2d[triangle[0]][1], heights[triangle[0]])
                dv2 = "{0} {1} {2}".format(points2d[triangle[1]][0], points2d[triangle[1]][1], heights[triangle[1]])
                dv3 = "{0} {1} {2}".format(points2d[triangle[2]][0], points2d[triangle[2]][1], heights[triangle[2]])

                debug.write("POLYGON Z(({0},{1},{2})) \n".format(dv1, dv2, dv3))

                triangles3d.append([v1, v2, v3])
        topology = TerrainTopology(geometries=triangles3d, hasLighting=True)
        tile = TerrainTile(topology=topology)

        dir_path = os.path.dirname(path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        if os.path.exists(path):
            os.remove(path)
        #tile.toFile(path)
        debug_tile = EditableTerrainTile(tile)
        debug_tile.toWKT("{0}.wkt".format(path))
