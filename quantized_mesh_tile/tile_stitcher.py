# -*- coding: utf-8 -*-

from __future__ import print_function
from operator import itemgetter
from unittest.case import _AssertRaisesContext

from . import cartesian3d as c3d, terrain


def get_next_by_key_and_value(edge_connections, index, edge_side):
    if index == len(edge_connections):
        return edge_connections[index]

    edge_connection_next = edge_connections[index]
    while not edge_connection_next.is_side(edge_side):
        index += 1
        edge_connection_next = edge_connections[index]

    return edge_connection_next


def get_previous_by_key_and_value(edge_connections, index, edge_side):
    if index == 0:
        return edge_connections[index]

    edge_connection_prev = edge_connections[index]
    while not edge_connection_prev.is_side(edge_side):
        index -= 1
        edge_connection_prev = edge_connections[index]

    return edge_connection_prev


class EdgeConnection(object):
    BOTH_SIDES = 2
    ONE_SIDE = 1

    def __init__(self, edge_info, edge_index):
        self.edge_info = edge_info
        self.edge_index = edge_index
        self._side_vertices = {}

    def __repr__(self):
        msg = '[{0}] -> ({1})'.format(self.edge_index, self._side_vertices)
        return msg

    def add_side(self, edge_side, side_vertex):
        self._side_vertices[edge_side] = side_vertex

    def get_side_vertex(self, edge_side):
        return self._side_vertices[edge_side]

    def get_side_vertices(self):
        return dict(self._side_vertices)

    def is_complete(self):
        size = len(self._side_vertices.values())
        return EdgeConnection.BOTH_SIDES == size

    def is_broken_on_center(self):
        return self.is_broken_on(self.edge_info)

    def is_broken_on_neighbour(self):
        return self.is_broken_on('c')

    def is_broken_on(self, edge_side):
        size = len(self._side_vertices.values())
        return EdgeConnection.ONE_SIDE == size and self._side_vertices.has_key(edge_side)

    def is_side(self, edge_side):
        return self._side_vertices.has_key(edge_side)


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
        center_vertices = []
        neighbour_vertices = []
        if center_bbox['west'] == neighbour_bbox['east']:
            center_vertices = self._center.get_edge_vertices('w')
            neighbour_vertices = neighbour_tile.get_edge_vertices('e')
        if center_bbox['east'] == neighbour_bbox['west']:
            center_vertices = self._center.get_edge_vertices('e')
            neighbour_vertices = neighbour_tile.get_edge_vertices('w')
        if center_bbox['north'] == neighbour_bbox['south']:
            center_vertices = self._center.get_edge_vertices('n')
            neighbour_vertices = neighbour_tile.get_edge_vertices('s')
        if center_bbox['south'] == neighbour_bbox['north']:
            center_vertices = self._center.get_edge_vertices('s')
            neighbour_vertices = neighbour_tile.get_edge_vertices('n')

        return center_vertices, neighbour_vertices

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
                        weighted_normals.extend(
                            self._neighbours[v['edge_info']].calculate_weighted_normals_for(triangles))
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
                    weighted_normals = self._neighbours[v['edge_info']].calculate_weighted_normals_for([triangle])
                    neighbour_weighted_normals[center_vertex_index] = weighted_normals

        return neighbour_weighted_normals

    def _find_edge_vertices(self):
        base_resolution = 256
        edge_vertices = []
        for edge_info, neighbour_tile in self._neighbours.items():
            single_edge_vertices = {}
            edge_connections = []
            edge_index = 0  # assume south>|<north
            if edge_info in ['w', 'e']:  # assume west>|<east
                edge_index = 1

            center_indices, neighbour_indices = self._get_edge_indices(neighbour_tile)
            for center_index in center_indices:
                c_uv = (self._center.u[center_index], self._center.v[center_index])
                # scaled_uv = self.scale_down(uv, base_resolution)
                c_key = '{}_{:05}'.format(edge_info, c_uv[edge_index])
                edge_connection = EdgeConnection(edge_info, c_uv[edge_index])
                edge_connection.add_side('c', center_index)
                single_edge_vertices[c_key] = edge_connection
            for neighbour_index in neighbour_indices:
                n_uv = (neighbour_tile.u[neighbour_index], neighbour_tile.v[neighbour_index])
                # scaled_uv = self.scale_down(uv, base_resolution)
                n_key = '{}_{:05}'.format(edge_info, n_uv[edge_index])

                if single_edge_vertices.has_key(n_key):
                    single_edge_vertices[n_key].add_side(edge_info, neighbour_index)
                else:
                    edge_connection = EdgeConnection(edge_info, n_uv[edge_index])
                    edge_connection.add_side(edge_info, neighbour_index)
                    single_edge_vertices[n_key] = edge_connection

            edge_connections = sorted(single_edge_vertices.values(), key=lambda x: x.edge_index, reverse=False)

            edge_vertices.append(edge_connections)

        return edge_vertices

    def _stitch_edges(self, edge_connections):

        for edge in edge_connections:
            for index in range(len(edge)):
                edge_connection = edge[index]

                # wenn vertex in c und n, dann nur höhe(c und n) angleichen
                if edge_connection.is_complete():
                    # FIXME  Höhenberechnung führt möglicherweise zu Fehler, wenn neue Höhe kleiner/größer als MIN/MAX
                    self._update_height_to_even(edge_connection)
                elif edge_connection.is_broken_on_neighbour():
                    # wenn vertex nur in c, dann triangle in n von vertex-1 und vertex+1 splitten
                    vertex_prev = self._get_prev_vertex(index, edge, edge_connection.edge_info)
                    vertex_next = self._get_next_vertex(index, edge, edge_connection.edge_info)

                    triangle = self._neighbours[edge_connection.edge_info].find_triangle_of(vertex_prev, vertex_next)
                    if triangle is None:
                        raise Exception('No triangle found for Vertex')
                    vertex_llh_insert = self._center.get_llh(edge_connection.get_side_vertex('c'))
                    vertex_new = self._neighbours[edge_connection.edge_info].split_triangle(triangle, vertex_prev,
                                                                                               vertex_next,
                                                                                               vertex_llh_insert)
                    edge_connection.add_side(edge_connection.edge_info,vertex_new)
                else:
                    # wenn vertex nur in n, dann triangle in c von c-vertex-1 und c-vertex+1 splitten
                    vertex_prev = self._get_prev_vertex(index, edge, 'c')
                    vertex_next = self._get_next_vertex(index, edge, 'c')

                    triangle = self._center.find_triangle_of(vertex_prev, vertex_next)
                    if triangle is None:
                        raise Exception('No triangle found for Vertex')

                    vertex_llh_insert = self._neighbours[edge_connection.edge_info].get_llh(edge_connection.get_side_vertex(edge_connection.edge_info))
                    vertex_new = self._center.split_triangle(triangle, vertex_prev, vertex_next, vertex_llh_insert)

                    edge_connection.add_side('c',vertex_new)

    def _harmonize_normals(self, neighbour_weighted_normals):
        for center_vertex_index, n_weighted_normals in neighbour_weighted_normals.items():

            center_triangles = self._center.find_all_triangles_of(center_vertex_index)
            weighted_normals = self._center.calculate_weighted_normals_for(center_triangles)
            weighted_normals.extend(n_weighted_normals)

            normal_vertex = [0, 0, 0]
            for w_n in weighted_normals:
                normal_vertex = c3d.add(normal_vertex, w_n)

            normal_vertex = c3d.normalize(normal_vertex)
            self._center.set_normal(center_vertex_index, normal_vertex)

    def _build_normals(self, edge_connections):
        self._center.rebuild_h()
        for n in self._neighbours.values():
            n.rebuild_h()

        for edge in edge_connections:
            for edge_connection in edge:
                center_vertex_index = edge_connection.get_side_vertex('c')

                neighbour_vertex_indices = {
                    edge_connection.edge_info: edge_connection.get_side_vertex(edge_connection.edge_info)}

                center_triangles = self._center.find_all_triangles_of(center_vertex_index)
                weighted_normals = self._center.calculate_weighted_normals_for(center_triangles, center_vertex_index)

                neighbour_triangles = []
                for neighbour_info, vertex_index in neighbour_vertex_indices.items():
                    neighbour_tile = self._neighbours[neighbour_info]
                    neighbour_triangles.extend(neighbour_tile.find_all_triangles_of(vertex_index))

                weighted_normals += neighbour_tile.calculate_weighted_normals_for(neighbour_triangles, vertex_index)

                normal_vertex = [0, 0, 0]
                for w_n in weighted_normals:
                    normal_vertex = c3d.add(normal_vertex, w_n)

                normal_vertex = c3d.normalize(normal_vertex)
                self._center.set_normal(center_vertex_index, normal_vertex)
                for neighbour_info, vertex_index in neighbour_vertex_indices.items():
                    neighbour_tile = self._neighbours[neighbour_info]
                    neighbour_tile.set_normal(vertex_index, normal_vertex)

    def _get_next_vertex(self, index, edge_connections, edge_side):
        edge_connection_next = get_next_by_key_and_value(edge_connections, index, edge_side)
        vertex_next = edge_connection_next.get_side_vertex(edge_side)
        return vertex_next

    def _get_prev_vertex(self, index, edge_connections, edge_side):
        edge_connection_prev = get_previous_by_key_and_value(edge_connections, index, edge_side)
        vertex_prev = edge_connection_prev.get_side_vertex(edge_side)
        return vertex_prev

    def _update_height_to_even(self, edge_connection):
        center_vertex_index = edge_connection.get_side_vertex('c')

        vertex_indices = edge_connection.get_side_vertices()

        vertex_heights = []
        for edge_info, vertex_index in vertex_indices.items():
            if edge_info is 'c':
                vertex_heights.append(self._center.get_height(vertex_index))
            else:
                vertex_heights.append(self._neighbours[edge_info].get_height(vertex_index))

        height = sum(vertex_heights) / len(vertex_heights)
        for edge_info in vertex_indices:
            if edge_info is 'c':
                self._center.set_height(center_vertex_index, height)
            else:
                self._neighbours[edge_info].set_height(vertex_indices[edge_info], height)

    def add_neighbour(self, neighbour_tile):
        edge_connection = self._get_edge_connection(neighbour_tile)
        self._neighbours[edge_connection] = neighbour_tile

    def harmonize_normals(self):
        edge_vertices = self._find_edge_vertices()
        sorted_edge_vertices = sorted(edge_vertices.items(), key=itemgetter(0))
        neighbour_weighted_normals = self._find_neighbour_triangles(sorted_edge_vertices)
        self._harmonize_normals(neighbour_weighted_normals)

    def stitch_together(self):
        edge_vertices = self._find_edge_vertices()
        # sorted_edge_vertices = sorted(edge_vertices.items(), key=itemgetter(0))
        self._stitch_edges(edge_vertices)
        self._build_normals(edge_vertices)

    def scale_down(self, uv, base_resolution):
        terrain_base_resolution = terrain.MAX
        u, v = uv
        scaled_u = int((u * base_resolution) / terrain_base_resolution)
        scaled_v = int((v * base_resolution) / terrain_base_resolution)
        return scaled_u, scaled_v
