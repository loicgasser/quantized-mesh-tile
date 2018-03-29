# -*- coding: utf-8 -*-

from __future__ import print_function
from operator import itemgetter

import math
from . import cartesian3d as c3d


def get_next_by_key_and_value(tuple_list, index, key, value):
    if index == len(tuple_list) - 1:
        return None

    k_next, v_next = tuple_list[index]
    hit = False
    while not hit:
        index += 1
        k_next, v_next = tuple_list[index]
        hit = value in v_next[key]

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

    def _get_edge_indices(self, neighbour_tile):
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

    def _find_neighbour_triangles(self, vertices):
        full_edge_point = 2
        neighbour_weighted_normals = {}
        for index in range(len(vertices)):
            k, v = vertices[index]
            center_vertex_index = v['vertex_indices'][v['vertex_side'].find('c')]

            # wenn vertex in c und n, dann alle gewichteten Normalen der Nachbar-Triangles berechnen
            if len(v['vertex_side']) >= full_edge_point:
                weighted_normals = []
                for edge_info in v['vertex_side']:
                    if edge_info is not 'c':
                        vertex_index = v['vertex_indices'][v['vertex_side'].index(edge_info)]
                        triangles = self._neighbours[v['edge_info']].find_all_triangles_of(vertex_index)
                        weighted_normals.extend(self._neighbours[v['edge_info']].calculate_weighted_normals_for(triangles))
                neighbour_weighted_normals[center_vertex_index] = weighted_normals

            elif 'c' == v['vertex_side']:
                # wenn vertex nur in c, dann triangle in n von vertex-1 und vertex+1 finden und die gewichtete Normale berechnen
                vertex_prev = self._get_prev_vertex(index, vertices, v['edge_info'])
                vertex_next = self._get_next_vertex(index, vertices, v['edge_info'])

                triangle_index = self._neighbours[v['edge_info']].find_triangle_of(vertex_prev, vertex_next)
                if not triangle_index:
                    print(" No Triangle found for {0}|{1} in {2} !".format(vertex_prev, vertex_next, edge_info))
                else:
                    triangle = self._neighbours[v['edge_info']].get_triangle(triangle_index)
                    weighted_normals=self._neighbours[v['edge_info']].calculate_weighted_normals_for([triangle])
                    neighbour_weighted_normals[center_vertex_index] = weighted_normals

        return neighbour_weighted_normals

    def _build_normals(self, neighbour_weighted_normals):
        for center_vertex_index, n_weighted_normals in neighbour_weighted_normals.items():

            center_triangles = self._center.find_all_triangles_of(center_vertex_index)
            weighted_normals = self._center.calculate_weighted_normals_for(center_triangles)
            weighted_normals.extend(n_weighted_normals)

            normal_vertex = [0, 0, 0]
            for w_n in weighted_normals:
                normal_vertex = c3d.add(normal_vertex, w_n)

            normal_vertex = c3d.normalize(normal_vertex)
            self._center.set_normal(center_vertex_index, normal_vertex)


    def _get_next_vertex(self, index, vertices, vertex_side_tag):
        k_next, v_next = get_next_by_key_and_value(vertices, index, 'vertex_side', vertex_side_tag)
        vertex_next = v_next['vertex_indices'][v_next['vertex_side'].index(vertex_side_tag)]
        return vertex_next

    def _get_prev_vertex(self, index, vertices, vertex_side_tag):
        k_prev, v_prev = get_previous_by_key_and_value(vertices, index, 'vertex_side', vertex_side_tag)
        vertex_prev = v_prev['vertex_indices'][v_prev['vertex_side'].index(vertex_side_tag)]
        return vertex_prev

    def _update_height_to_even(self, v):
        center_vertex_index = v['vertex_indices'][v['vertex_side'].find('c')]

        vertex_indices = {}
        for edge_info in v['vertex_side']:
            vertex_indices[edge_info] = v['vertex_indices'][v['vertex_side'].index(edge_info)]

        vertex_heights = []
        for edge_info, vertex_index in vertex_indices.items():
            if edge_info is 'c':
                vertex_heights.append(self._center.get_height(vertex_index))
            else:
                vertex_heights.append(self._neighbours[edge_info].get_height(vertex_index))

        height = sum(vertex_heights) / len(vertex_heights)
        for edge_info in v['vertex_side']:
            if edge_info is 'c':
                self._center.set_height(center_vertex_index, height)
            else:
                self._neighbours[edge_info].set_height(vertex_indices[edge_info], height)

    def _find_edge_vertices(self):
        edge_vertices = {}
        for edge_info, neighbour_tile in self._neighbours.items():

            edge_index = 0  # assume south>|<north
            if edge_info in ['w', 'e']:  # assume west>|<east
                edge_index = 1

            center_indices, neighbour_indices = self._get_edge_indices(neighbour_tile)
            key_prefix = int(math.fabs(edge_index - 1))
            for i in center_indices:
                uv = (self._center.u[i], self._center.v[i])
                key = '{}_{:05}'.format(edge_info, uv[edge_index])

                edge_vertices[key] = {'vertex_side': 'c', 'vertex_indices': [i], 'edge_info': edge_info}
            for i in neighbour_indices:
                uv = (neighbour_tile.u[i], neighbour_tile.v[i])

                key = '{}_{:05}'.format(edge_info, uv[edge_index])

                if key in edge_vertices.keys():
                    if edge_info not in edge_vertices[key]['vertex_side']:
                        edge_vertices[key]['vertex_indices'].append(i)
                        edge_vertices[key]['vertex_side'] += edge_info
                else:
                    edge_vertices[key] = {'vertex_side': edge_info, 'vertex_indices': [i], 'edge_info': edge_info}
        return edge_vertices

    def add_neighbour(self, neighbour_tile):
        edge_connection = self._get_edge_connection(neighbour_tile)
        self._neighbours[edge_connection] = neighbour_tile

    def stitch_together(self):
        edge_vertices = self._find_edge_vertices()
        sorted_edge_vertices = sorted(edge_vertices.items(), key=itemgetter(0))
        neighbour_weighted_normals = self._find_neighbour_triangles(sorted_edge_vertices)
        self._build_normals(neighbour_weighted_normals )
