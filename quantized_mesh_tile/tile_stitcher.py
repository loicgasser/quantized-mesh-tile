# -*- coding: utf-8 -*-

from __future__ import print_function
from operator import itemgetter

import numpy as np
from quantized_mesh_tile.utils import triangleArea

from . import cartesian3d as c3d

from quantized_mesh_tile.llh_ecef import LLH2ECEF


def get_next_by_key_and_value(tuple_list, index, key, value):
    if index == len(tuple_list) - 1:
        return None

    k_next, v_next = tuple_list[index]
    while value not in v_next[key]:
        index += 1
        k_next, v_next = tuple_list[index]

    return k_next, v_next


def get_previous_by_key_and_value(tuple_list, index, key, value):
    if index == 0:
        return None

    k_prev, v_prev = tuple_list[index]
    while value not in v_prev[key]:
        index -= 1
        k_prev, v_prev = tuple_list[index]

    return k_prev, v_prev


class TileStitcher(object):

    def __init__(self, center_tile):
        self._center = center_tile
        self.center_vertices = self._center.getVerticesCoordinates()
        self.neighbour_vertices = []

    def get_edge_connection(self, neighbour_tile):
        center_bbox = self._center.get_bounding_box()
        neighbour_bbox = neighbour_tile.get_bounding_box()

        if center_bbox['west'] == neighbour_bbox['east']:
            return 'west'
        if center_bbox['east'] == neighbour_bbox['west']:
            return 'east'
        if center_bbox['north'] == neighbour_bbox['south']:
            return 'north'
        if center_bbox['south'] == neighbour_bbox['north']:
            return 'south'
        return None

    def get_edge_indices(self, neighbour_tile):
        center_bbox = self._center.get_bounding_box()
        neighbour_bbox = neighbour_tile.get_bounding_box()

        if center_bbox['west'] == neighbour_bbox['east']:
            return self._center.westI, neighbour_tile.eastI
        if center_bbox['east'] == neighbour_bbox['west']:
            return self._center.eastI, neighbour_tile.westI
        if center_bbox['north'] == neighbour_bbox['south']:
            return self._center.northI, neighbour_tile.southI
        if center_bbox['south'] == neighbour_bbox['north']:
            return self._center.southI, neighbour_tile.northI

        return None, None

    def get_base_edge_indices(self, neighbour_tile):
        c_bbox = self._center.get_bounding_box()
        n_bbox = neighbour_tile.get_bounding_box()
        indices = []
        if c_bbox['west'] == n_bbox['east']:
            indices.append([c_bbox['west'], c_bbox['north']])
            indices.append([c_bbox['west'], c_bbox['south']])
        if c_bbox['east'] == n_bbox['west']:
            indices.append([c_bbox['west'], c_bbox['north']])
            indices.append([c_bbox['west'], c_bbox['south']])
        if c_bbox['north'] == n_bbox['south']:
            indices.append([c_bbox['west'], c_bbox['north']])
            indices.append([c_bbox['east'], c_bbox['north']])
        if c_bbox['south'] == n_bbox['north']:
            indices.append([c_bbox['west'], c_bbox['south']])
            indices.append([c_bbox['east'], c_bbox['south']])

        base_edge_indices = []
        for i in indices:
            for j in range(len(self.center_vertices)):
                if i[0] == self.center_vertices[j][0] and i[1] == self.center_vertices[j][1]:
                    base_edge_indices.append(j)

        return base_edge_indices

    def stitch_with(self, neighbour_tile):
        edge_connection = self.get_edge_connection(neighbour_tile)

        vertex_key_index = 1
        if edge_connection in ['north', 'south']:
            vertex_key_index = 0

        self.neighbour_vertices = neighbour_tile.getVerticesCoordinates()
        center_indices, neighbour_indices = self.get_edge_indices(neighbour_tile)
        base_edge_indices = self.get_base_edge_indices(neighbour_tile)

        edge_vertices = {}

        for i in base_edge_indices:
            uv = (self._center.u[i], self._center.v[i])
            key = '{:05}'.format(uv[vertex_key_index])
            edge_vertices[key] = {'vertex_side': 'c', 'vertex_indices': [i]}

        for i in center_indices:
            uv = (self._center.u[i], self._center.v[i])
            key = '{:05}'.format(uv[vertex_key_index])
            edge_vertices[key] = {'vertex_side': 'c', 'vertex_indices': [i]}

        for i in neighbour_indices:
            uv = (neighbour_tile.u[i], neighbour_tile.v[i])
            key = '{:05}'.format(uv[vertex_key_index])

            if key in edge_vertices.keys():
                if 'n' not in edge_vertices[key]['vertex_side']:
                    edge_vertices[key]['vertex_indices'].append(i)
                    edge_vertices[key]['vertex_side'] += 'n'
            else:
                edge_vertices[key] = {'vertex_side': 'n', 'vertex_indices': [i]}

        sorted_edge_vertices = sorted(edge_vertices.items(), key=itemgetter(0))

        for index in range(len(sorted_edge_vertices)):
            k, v = sorted_edge_vertices[index]
            print('{0}:{1} -> {2}'.format(index, k, v))

            # wenn vertex in c und n, dann nur höhe(c und n) angleichen
            if 'cn' == v['vertex_side']:
                center_vertex_index = v['vertex_indices'][v['vertex_side'].find('c')]
                neighbour_vertex_index = v['vertex_indices'][v['vertex_side'].find('n')]
                c_height = self.center_vertices[center_vertex_index][2]
                n_height = self.neighbour_vertices[neighbour_vertex_index][2]
                if c_height != n_height:
                    height = (c_height + n_height) / 2
                    self._center.set_height(center_vertex_index, height)
                    neighbour_tile.set_height(neighbour_vertex_index, height)

            # wenn vertex nur in c, dann triangle in n von vertex-1 und vertex+1 splitten
            if 'c' == v['vertex_side']:
                k_prev, v_prev = get_previous_by_key_and_value(sorted_edge_vertices, index, 'vertex_side', 'n')
                k_next, v_next = get_next_by_key_and_value(sorted_edge_vertices, index, 'vertex_side', 'n')

                vertex_prev = v_prev['vertex_indices'][v_prev['vertex_side'].index('n')]
                vertex_next = v_next['vertex_indices'][v_next['vertex_side'].index('n')]

                triangle = neighbour_tile.find_triangle_of(vertex_prev, vertex_next)
                vertex_insert = self.center_vertices[v['vertex_indices'][0]]
                vertex_new = neighbour_tile.split_triangle(triangle, vertex_prev, vertex_next, vertex_insert)

                v['vertex_side'] += 'n'
                v['vertex_indices'].append(vertex_new)

            # wenn vertex nur in n, dann triangle in c von c-vertex-1 und c-vertex+1 splitten
            if 'n' == v['vertex_side']:
                k_prev, v_prev = get_previous_by_key_and_value(sorted_edge_vertices, index, 'vertex_side', 'c')
                k_next, v_next = get_next_by_key_and_value(sorted_edge_vertices, index, 'vertex_side', 'c')

                vertex_prev = v_prev['vertex_indices'][v_prev['vertex_side'].index('c')]
                vertex_next = v_next['vertex_indices'][v_next['vertex_side'].index('c')]

                triangle = self._center.find_triangle_of(vertex_prev, vertex_next)
                vertex_insert = self.center_vertices[v['vertex_indices'][0]]
                vertex_new = self._center.split_triangle(triangle, vertex_prev, vertex_next, vertex_insert)

                v['vertex_side'] += 'c'
                v['vertex_indices'].append(vertex_new)

        self.neighbour_vertices = neighbour_tile.getVerticesCoordinates()
        self.center_vertices = self._center.getVerticesCoordinates()


        # ...und dann normalen neu berechnen
        # die jetzt in center- und neighbour-tile identischen vertices und die gewichteten normalen der triangles neu berechnen
        # normalen der verbundenen base-edge-vertices addieren

        for k, v in sorted_edge_vertices:
            print(v)
            center_vertex_index = v['vertex_indices'][v['vertex_side'].index('c')]
            neighbour_vertex_index = v['vertex_indices'][v['vertex_side'].index('n')]

            weighted_normals = []
            all_triangles = self._center.find_all_triangles_of(center_vertex_index)
            for triangle in all_triangles:
                llh0 = self.center_vertices[triangle[0]]
                llh1 = self.center_vertices[triangle[1]]
                llh2 = self.center_vertices[triangle[2]]
                v0 = LLH2ECEF(llh0[0], llh0[1], llh0[2])
                v1 = LLH2ECEF(llh1[0], llh1[1], llh1[2])
                v2 = LLH2ECEF(llh2[0], llh2[1], llh2[2])

                normal = np.cross(c3d.subtract(v1, v0), c3d.subtract(v2, v0))
                area = triangleArea(v0, v1)

                weighted_normals.append(normal * area)

            for triangle in neighbour_tile.find_all_triangles_of(neighbour_vertex_index):
                llh0 = self.neighbour_vertices[triangle[0]]
                llh1 = self.neighbour_vertices[triangle[1]]
                llh2 = self.neighbour_vertices[triangle[2]]
                v0 = LLH2ECEF(llh0[0], llh0[1], llh0[2])
                v1 = LLH2ECEF(llh1[0], llh1[1], llh1[2])
                v2 = LLH2ECEF(llh2[0], llh2[1], llh2[2])

                normal = np.cross(c3d.subtract(v1, v0), c3d.subtract(v2, v0))
                area = triangleArea(v0, v1)

                weighted_normals.append(normal * area)

            normal_vertex = [0, 0, 0]
            for w_n in weighted_normals:
                normal_vertex = c3d.add(normal_vertex, w_n)

            normal_vertex = c3d.normalize(normal_vertex)
            self._center.set_normal(center_vertex_index, normal_vertex)
            neighbour_tile.set_normal(neighbour_vertex_index, normal_vertex)
