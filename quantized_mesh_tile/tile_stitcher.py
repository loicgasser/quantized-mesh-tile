# -*- coding: utf-8 -*-

from __future__ import print_function

from quantized_mesh_tile.editable_terrain import EditableTerrainTile
from quantized_mesh_tile.global_geodetic import GlobalGeodetic

from . import cartesian3d as c3d


def get_next_by_key_and_value(edge_connections, index, edge_side):
    """

    :param edge_connections:
    :param index:
    :param edge_side:
    :return:
    """
    if index == len(edge_connections):
        return edge_connections[index]

    edge_connection_next = edge_connections[index]
    while not edge_connection_next.is_side(edge_side):
        index += 1
        edge_connection_next = edge_connections[index]

    return edge_connection_next


def get_previous_by_key_and_value(edge_connections, index, edge_side):
    """

    :param edge_connections:
    :param index:
    :param edge_side:
    :return:
    """
    if index == 0:
        return edge_connections[index]

    edge_connection_prev = edge_connections[index]
    while not edge_connection_prev.is_side(edge_side):
        index -= 1
        edge_connection_prev = edge_connections[index]

    return edge_connection_prev


def get_neighbours(z, x, y):
    return {'west': (z, x - 1, y),
            'north': (z, x, y + 1),
            'south': (z, x, y - 1),
            'east': (z, x + 1, y)}


def get_neighbours_south_east(z, x, y):
    return {'south': (z, x, y - 1),
            'east': (z, x + 1, y)}


def load_tile(terrain_path, x, y, z):
    """

    :rtype: EditableTerrainTile
    """
    geodetic = GlobalGeodetic(True)
    [minx, miny, maxx, maxy] = geodetic.TileBounds(x, y, z)
    tile = EditableTerrainTile(west=minx, south=miny, east=maxx, north=maxy)
    tile.fromFile(terrain_path, has_lighting=True)
    return tile


class EdgeConnection(object):
    """
    Property class, to store information of points/nodes which
    participating on a tile edge
    """
    BOTH_SIDES = 2
    ONE_SIDE = 1

    def __init__(self, edge_info, edge_index):
        self.edge_index = edge_index
        self.edge_info = edge_info
        self._side_vertices = {}

    def __repr__(self):
        msg = 'E:{0} [{1}] -> ({2})'.format(self.edge_info, self.edge_index,
                                            self._side_vertices)
        return msg

    def add_side(self, edge_side, side_vertex):
        """
        Adds the side information to the edge-connection
        :param edge_side: the participating side of the edge ('w','n','e','s')
        :param side_vertex: the index of the vertex in the list of vertices of the
        given side (tile)
        """
        self._side_vertices[edge_side] = side_vertex

    def get_side_vertex(self, edge_side):
        """
        Gets the index of the vertex in the list of vertices of the given side (tile)
        :rtype: integer
        :param edge_side: the participating side of the edge ('w','n','e','s')
        :return: the index of the vertex, based on the given side
        """
        return self._side_vertices[edge_side]

    @property
    def get_side_vertices(self):
        return dict(self._side_vertices)

    @property
    def is_complete(self):
        size = len(self._side_vertices.values())
        return EdgeConnection.BOTH_SIDES == size

    @property
    def is_broken_on_center(self):
        return self.is_broken_on(self.edge_info)

    @property
    def is_broken_on_neighbour(self):
        return self.is_broken_on('c')

    def is_broken_on(self, edge_side):
        # type: (str) -> bool
        size = len(self._side_vertices.values())
        return EdgeConnection.ONE_SIDE == size and self.is_side(edge_side)

    def is_side(self, edge_side):
        # type: (str) -> bool
        """

        :param edge_side: the participating side of the edge ('w','n','e','s')
        :return: Returns True, if a vertex of the given side is registered in this
        connection
        """
        return edge_side in self._side_vertices.keys()


class TileStitcher(object):
    """
        The worker class to stitch terrain files together

        Constructor arguments:

        ''center_tile''
            the the center tile, from which the neighbouring edges are stitched,
            if neighbour tiles are added


        Usage example::
        import os
        from quantized_mesh_tile.tile_stitcher import TileStitcher, load_tile,
                                                        get_neighbours_south_east

        directory_base_path = '/data/terrain/'
        levels = [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]

        #walk through level and file hierarchy
        for level in levels:
            directory_path = os.path.join(directory_base_path, str(level))
            terrain_files = []
            for root, dirs, files in os.walk(directory_path, topdown=True):
                for name in files:
                    candidate_path = os.path.join(root, name)
                    if candidate_path.endswith('.terrain'):
                        terrain_files.append(candidate_path)

            for tile_path in terrain_files:

                y = int(os.path.basename(tile_path).split('.')[0])
                x = int(os.path.basename(os.path.dirname(tile_path)))
                print('processing {0} ...'.format(tile_path))
                neighbours = get_neighbours_south_east(level, x, y)
                center_tile = tile_stitcher.load_tile(tile_path, x, y, level)

                stitcher = TileStitcher(center_tile)
                for n, tile_info in neighbours.items():
                    n_z, n_x, n_y = tile_info

                    neighbour_path = os.path.join(directory_path,
                                    '%s/%s.terrain' % (n_x, n_y))
                    if os.path.exists(neighbour_path):
                        print("\tadding Neighbour {0}...".format(neighbour_path))
                        tile = tile_stitcher.load_tile(neighbour_path, n_x, n_y, level)
                        stitcher.add_neighbour(tile)
                stitcher.stitch_together()
                stitcher.save()
    """

    def __init__(self, center_tile):
        self._center = center_tile
        self._neighbours = {}

    def _get_edge_connection(self, neighbour_tile):
        center_bbox = self._center.get_bounding_box
        neighbour_bbox = neighbour_tile.get_bounding_box

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
        center_bbox = self._center.get_bounding_box
        neighbour_bbox = neighbour_tile.get_bounding_box
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

    def _find_edge_connections(self):

        edge_connections = []
        for edge_info, neighbour_tile in self._neighbours.items():
            single_edge_vertices = {}
            edge_index = 0  # assume south>|<north
            if edge_info in ['w', 'e']:  # assume west>|<east
                edge_index = 1

            center_indices, neighbour_indices = self._get_edge_indices(neighbour_tile)
            for center_index in center_indices:
                c_uv = (self._center.u[center_index], self._center.v[center_index])
                c_key = '{}_{:05}'.format(edge_info, c_uv[edge_index])
                edge_connection = EdgeConnection(edge_info, c_uv[edge_index])
                edge_connection.add_side('c', center_index)
                single_edge_vertices[c_key] = edge_connection
            for neighbour_index in neighbour_indices:
                n_uv = (neighbour_tile.u[neighbour_index],
                        neighbour_tile.v[neighbour_index])
                n_key = '{}_{:05}'.format(edge_info, n_uv[edge_index])

                if n_key in single_edge_vertices.keys():
                    single_edge_vertices[n_key].add_side(edge_info, neighbour_index)
                else:
                    edge_connection = EdgeConnection(edge_info, n_uv[edge_index])
                    edge_connection.add_side(edge_info, neighbour_index)
                    single_edge_vertices[n_key] = edge_connection

            single_edge_connections = sorted(single_edge_vertices.values(),
                                             key=lambda x: x.edge_index,
                                             reverse=False)

            edge_connections.append(single_edge_connections)

        return edge_connections

    def _stitch_edges(self, edge_connections):

        for edge in edge_connections:
            for index in range(len(edge)):
                edge_connection = edge[index]

                edge_info = edge_connection.edge_info
                neighbour = self._neighbours[edge_info]
                if edge_connection.is_complete:
                    self._update_height_to_even(edge_connection)
                elif edge_connection.is_broken_on_neighbour:
                    vertex_prev = self._get_prev_vertex(index, edge, edge_info)
                    vertex_next = self._get_next_vertex(index, edge, edge_info)

                    coordinate_new = self._center.get_coordinate(
                        edge_connection.get_side_vertex('c'))
                    vertex_new = neighbour.find_and_split_triangle(vertex_prev,
                                                                   vertex_next,
                                                                   coordinate_new)
                    edge_connection.add_side(edge_info, vertex_new)
                else:
                    # wenn vertex nur in n, dann triangle in c
                    # von c-vertex-1 und c-vertex+1 splitten
                    vertex_prev = self._get_prev_vertex(index, edge, 'c')
                    vertex_next = self._get_next_vertex(index, edge, 'c')

                    coordinate_new = neighbour.get_coordinate(
                        edge_connection.get_side_vertex(edge_info))
                    vertex_new = self._center.find_and_split_triangle(vertex_prev,
                                                                      vertex_next,
                                                                      coordinate_new)

                    edge_connection.add_side('c', vertex_new)

    def _harmonize_normals(self, edge_connections):
        center = self._center
        for edge in edge_connections:
            for edge_connection in edge:
                center_vertex_index = edge_connection.get_side_vertex('c')

                side_vertex = edge_connection.get_side_vertex(edge_connection.edge_info)
                neighbour_vertex_indices = {edge_connection.edge_info: side_vertex}

                center_triangles = center.find_all_triangles_of(center_vertex_index)
                normals = center.calculate_weighted_normals_for(center_triangles)

                for neighbour_info, vertex_index in neighbour_vertex_indices.items():
                    neighbour_tile = self._neighbours[neighbour_info]
                    triangles = neighbour_tile.find_all_triangles_of(vertex_index)
                    normals.extend(neighbour_tile.calculate_weighted_normals_for(
                        triangles))

                normal_vertex = [0, 0, 0]
                for w_n in normals:
                    normal_vertex = c3d.add(normal_vertex, w_n)

                normal_vertex = c3d.normalize(normal_vertex)
                center.set_normal(center_vertex_index, normal_vertex)
                for neighbour_info, vertex_index in neighbour_vertex_indices.items():
                    neighbour_tile = self._neighbours[neighbour_info]
                    neighbour_tile.set_normal(vertex_index, normal_vertex)

    def _build_normals(self, edge_connections):
        center = self._center
        center.rebuild_h()
        for n in self._neighbours.values():
            n.rebuild_h()

        for edge in edge_connections:
            for edge_connection in edge:
                center_vertex_index = edge_connection.get_side_vertex('c')

                side_vertex = edge_connection.get_side_vertex(edge_connection.edge_info)
                neighbour_vertex_indices = {edge_connection.edge_info: side_vertex}

                center_triangles = center.find_all_triangles_of(center_vertex_index)
                normals = center.calculate_weighted_normals_for(center_triangles)

                for neighbour_info, vertex_index in neighbour_vertex_indices.items():
                    neighbour_tile = self._neighbours[neighbour_info]
                    triangles = neighbour_tile.find_all_triangles_of(vertex_index)
                    normals.extend(neighbour_tile.calculate_weighted_normals_for(
                        triangles))

                normal_vertex = [0, 0, 0]
                for w_n in normals:
                    normal_vertex = c3d.add(normal_vertex, w_n)

                normal_vertex = c3d.normalize(normal_vertex)
                center.set_normal(center_vertex_index, normal_vertex)
                for neighbour_info, vertex_index in neighbour_vertex_indices.items():
                    neighbour_tile = self._neighbours[neighbour_info]
                    neighbour_tile.set_normal(vertex_index, normal_vertex)

    @staticmethod
    def _get_next_vertex(index, edge_connections, edge_side):
        edge_connection_next = get_next_by_key_and_value(edge_connections,
                                                         index,
                                                         edge_side)
        vertex_next = edge_connection_next.get_side_vertex(edge_side)
        return vertex_next

    @staticmethod
    def _get_prev_vertex(index, edge_connections, edge_side):
        edge_connection_prev = get_previous_by_key_and_value(edge_connections,
                                                             index,
                                                             edge_side)
        vertex_prev = edge_connection_prev.get_side_vertex(edge_side)
        return vertex_prev

    def _update_height_to_even(self, edge_connection):
        center_vertex_index = edge_connection.get_side_vertex('c')

        vertex_indices = edge_connection.get_side_vertices

        vertex_heights = []
        for edge_info, vertex_index in vertex_indices.items():
            if edge_info is 'c':
                vertex_heights.append(self._center.get_height(vertex_index))
            else:
                neighbour = self._neighbours[edge_info]
                vertex_heights.append(neighbour.get_height(vertex_index))

        height = sum(vertex_heights) / len(vertex_heights)
        for edge_info in vertex_indices:
            if edge_info is 'c':
                self._center.set_height(center_vertex_index, height)
            else:
                neighbour = self._neighbours[edge_info]
                neighbour.set_height(vertex_indices[edge_info], height)

    def add_neighbour(self, neighbour_tile):
        edge_connection = self._get_edge_connection(neighbour_tile)
        self._neighbours[edge_connection] = neighbour_tile

    def harmonize_normals(self):
        edge_connections = self._find_edge_connections()
        self._harmonize_normals(edge_connections)

    def stitch_together(self):
        edge_connections = self._find_edge_connections()
        self._stitch_edges(edge_connections)
        self._build_normals(edge_connections)

    def save(self):
        self._center.save()
        for edge_info, neighbour_tile in self._neighbours.items():
            neighbour_tile.save()

    def save_to(self, dir_path):
        self._center.save_to(dir_path)
        for edge_info, neighbour_tile in self._neighbours.items():
            neighbour_tile.save_to(dir_path)
