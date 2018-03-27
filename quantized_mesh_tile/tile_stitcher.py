# -*- coding: utf-8 -*-

from __future__ import print_function
from operator import itemgetter
from . import cartesian3d as c3d


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

    def stitch_with(self, neighbour_tile):
        edge_connection = self.get_edge_connection(neighbour_tile)
        center_new_vertices_count = 0
        neighbour_new_vertices_count = 0
        merged_vertices_count = 0

        edge_index = 0  # assume south>|<north
        if edge_connection in ['west', 'east']:  # assume west>|<east
            edge_index = 1

        edge_vertices = self.find_edge_vertices(neighbour_tile, edge_index)

        sorted_edge_vertices = sorted(edge_vertices.items(), key=itemgetter(0))

        for index in range(len(sorted_edge_vertices)):
            k, v = sorted_edge_vertices[index]

            # wenn vertex in c und n, dann nur höhe(c und n) angleichen
            if 'cn' == v['vertex_side']:
                self.update_height_to_even(neighbour_tile, v)
                merged_vertices_count+=1


            # wenn vertex nur in c, dann triangle in n von vertex-1 und vertex+1 splitten
            if 'c' == v['vertex_side']:
                vertex_prev = self.get_prev_vertex(index, sorted_edge_vertices, 'n')
                vertex_next = self.get_next_vertex(index, sorted_edge_vertices, 'n')

                triangle = neighbour_tile.find_triangle_of(vertex_prev, vertex_next)
                vertex_llh_insert = self._center.get_llh(v['vertex_indices'][0])
                vertex_new = neighbour_tile.split_triangle(triangle, vertex_prev, vertex_next, vertex_llh_insert)
                neighbour_new_vertices_count+=1
                v['vertex_side'] += 'n'
                v['vertex_indices'].append(vertex_new)

            # wenn vertex nur in n, dann triangle in c von c-vertex-1 und c-vertex+1 splitten
            if 'n' == v['vertex_side']:
                vertex_prev = self.get_prev_vertex(index, sorted_edge_vertices, 'c')
                vertex_next = self.get_next_vertex(index, sorted_edge_vertices, 'c')

                triangle = self._center.find_triangle_of(vertex_prev, vertex_next)
                vertex_llh_insert = neighbour_tile.get_llh(v['vertex_indices'][0])
                vertex_new = self._center.split_triangle(triangle, vertex_prev, vertex_next, vertex_llh_insert)
                center_new_vertices_count+=1

                v['vertex_side'] += 'c'
                v['vertex_indices'].append(vertex_new)

        for k, v in sorted_edge_vertices:
            center_vertex_index = v['vertex_indices'][v['vertex_side'].index('c')]
            neighbour_vertex_index = v['vertex_indices'][v['vertex_side'].index('n')]

            center_triangles = self._center.find_all_triangles_of(center_vertex_index)
            weighted_normals = self._center.calculate_normals_for(center_triangles)

            neighbour_triangles = neighbour_tile.find_all_triangles_of(neighbour_vertex_index)
            weighted_normals += neighbour_tile.calculate_normals_for(neighbour_triangles)

            normal_vertex = [0, 0, 0]
            for w_n in weighted_normals:
                normal_vertex = c3d.add(normal_vertex, w_n)

            normal_vertex = c3d.normalize(normal_vertex)
            self._center.set_normal(center_vertex_index, normal_vertex)
            neighbour_tile.set_normal(neighbour_vertex_index, normal_vertex)


        print("Tiles stitched together. {0} Vertices added in Center-Tile, {1} Vertices added in Neighbour-Tile. {2} Vertices with balanced Height-Values".format(center_new_vertices_count,neighbour_new_vertices_count, merged_vertices_count))
        


    def get_next_vertex(self, index, sorted_edge_vertices, vertex_side_tag):
        k_next, v_next = get_next_by_key_and_value(sorted_edge_vertices, index, 'vertex_side', vertex_side_tag)
        vertex_next = v_next['vertex_indices'][v_next['vertex_side'].index(vertex_side_tag)]
        return vertex_next

    def get_prev_vertex(self, index, sorted_edge_vertices, vertex_side_tag):
        k_prev, v_prev = get_previous_by_key_and_value(sorted_edge_vertices, index, 'vertex_side', vertex_side_tag)
        vertex_prev = v_prev['vertex_indices'][v_prev['vertex_side'].index(vertex_side_tag)]
        return vertex_prev

    def update_height_to_even(self, neighbour_tile, v):
        center_vertex_index = v['vertex_indices'][v['vertex_side'].find('c')]
        neighbour_vertex_index = v['vertex_indices'][v['vertex_side'].find('n')]
        c_height = self._center.get_height(center_vertex_index)
        n_height = neighbour_tile.get_height(neighbour_vertex_index)
        if c_height != n_height:
            height = (c_height + n_height) / 2
            self._center.set_height(center_vertex_index, height)
            neighbour_tile.set_height(neighbour_vertex_index, height)

    def find_edge_vertices(self, neighbour_tile, edge_index):
        edge_vertices = {}
        center_indices, neighbour_indices = self.get_edge_indices(neighbour_tile)
        for i in center_indices:
            uv = (self._center.u[i], self._center.v[i])
            key = '{:05}'.format(uv[edge_index])
            edge_vertices[key] = {'vertex_side': 'c', 'vertex_indices': [i]}
        for i in neighbour_indices:
            uv = (neighbour_tile.u[i], neighbour_tile.v[i])
            key = '{:05}'.format(uv[edge_index])

            if key in edge_vertices.keys():
                if 'n' not in edge_vertices[key]['vertex_side']:
                    edge_vertices[key]['vertex_indices'].append(i)
                    edge_vertices[key]['vertex_side'] += 'n'
            else:
                edge_vertices[key] = {'vertex_side': 'n', 'vertex_indices': [i]}
        return edge_vertices
