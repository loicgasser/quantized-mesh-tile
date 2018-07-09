# -*- coding: utf-8 -*-
import os

import numpy as np
from future.utils import old_div

from quantized_mesh_tile import TerrainTile
from quantized_mesh_tile.llh_ecef import LLH2ECEF
from quantized_mesh_tile.terrain import MAX, lerp
from quantized_mesh_tile.utils import triangleArea
from . import cartesian3d as c3d

null_normal = [0, 0, 0]


class EditableTerrainTile(TerrainTile):
    """
    Helper class to edit a given terrain tile on the edges.
    Changes are possible on specified Heights, Triangles and Normals.


    """

    def __init__(self, *args, **kwargs):
        super(EditableTerrainTile, self).__init__(*args, **kwargs)
        self.is_index_dirty = False
        self._changed_heights = []
        self._file_path = None
        self._gzipped = False

    def get_edge_vertices(self, edge):
        """
        Returns the indices of vertices on the defined edge.
        :param edge: the edge of the tile. Specified by the flags 'w','n','e','s'
                    for west-, north-, east- and  south-edge
        :return: Array of integers
        """
        if 'w' == edge:
            edge_value = 0
            search_array = self.u
        elif 'e' == edge:
            edge_value = MAX
            search_array = self.u
        elif 'n' == edge:
            edge_value = MAX
            search_array = self.v
        elif 's' == edge:
            edge_value = 0
            search_array = self.v
        indices = [i for i, x in enumerate(search_array) if x == edge_value]
        return indices

    def get_edge_coordinates(self, edge):
        # type: (string) -> Array
        """
        Returns a array of coordinate-tupels for all vertices on the specified edge
        :return: Array of 3d coordinates (3-tupel of float; x,y,z)
        :param edge: the edge of the tile. Specified by the flags 'w','n','e','s'
                    for west-, north-, east- and  south-edge
        """
        edge_coordinates = []
        coordinates = self.getVerticesCoordinates()
        vertices = self.get_edge_vertices(edge)
        for vertex in vertices:
            edge_coordinates.append(coordinates[vertex])

        return edge_coordinates

    @property
    def get_bounding_box(self):
        """
        Returns the bounding box of the tile in WGS84 degree
        :return: Dictionary of floats for boundingbox of the tile with
                keys ['west','east','north', 'south']
        """
        return {'west': self._west,
                'east': self._east,
                'north': self._north,
                'south': self._south}

    def set_normal(self, index, normal):
        # type: (int, Array) -> void
        """
        Sets the normal vector for the vertex which is specified with the index,
        changing a normal vector causes a rebuild of all indices
        :param index: index of the vertex
        :param normal: the normal vector in the form [x,y,z]
        """
        self.is_index_dirty = True
        self.vLight[index] = normal

    def set_height(self, index, height):
        # type: (int, float) -> void
        """
        Sets the height for the vertex  which is specified with the index,
        if the new height is out of the tile height range (min/max height),
        all heights are requantized during save-process
        :param index: index of the vertex
        :param height:the height at the specified vertex index
        """
        height_is_dirty = False

        if height < self.header['minimumHeight']:
            height_is_dirty = True
        if self.header['maximumHeight'] < height:
            height_is_dirty = True

        if height_is_dirty or self._changed_heights:
            if not self._changed_heights:
                self._changed_heights = [self._dequantize_height(x) for x in self.h]
            self._changed_heights[index] = height
        else:
            self.h[index] = self._quantize_height(height)

    def get_height(self, index):
        # type: (int) -> float
        """
        Returns the dequantized height at the specified vertex index
        :param index: index of the vertex
        :return: the height at the specified vertex
        """
        height = self._dequantize_height(self.h[index])
        return height

    def get_coordinate(self, index):
        """
        Returns the dequantized coordinate at the specified vertex index
        :param index: index of the vertex
        :return: the wgs84 coordinate in the form [longitude, latitude, height]
        """
        return self._uvh_to_llh(index)

    def find_triangle_of(self, vertex_prev, vertex_next):
        indices = iter(self.indices)
        for i in range(0, len(self.indices) - 1, 3):
            vi1 = next(indices)
            vi2 = next(indices)
            vi3 = next(indices)
            triangle = (vi1, vi2, vi3)
            if vertex_prev in triangle and vertex_next in triangle:
                return i / 3

        return None

    def find_all_triangles_of(self, vertex):
        """
        Searches for all triangles of the specified vertex index
        and returns the list of triangles
        :param vertex: the vertex index
        :return: Array of triangle indices
        """
        triangles = []
        for triangle in self._get_triangles():
            if vertex in triangle:
                triangles.append(triangle)

        return triangles

    def _get_triangles(self):
        indices = iter(self.indices)
        for i in range(0, len(self.indices), 3):
            vi1 = next(indices)
            vi2 = next(indices)
            vi3 = next(indices)
            triangle = (vi1, vi2, vi3)
            yield triangle

    def get_triangle(self, index):
        """
        Returns the triangle for the specified index
        :param index: the index of the triangle
        :return: array of vertex indeces
        """
        offset = index * 3

        vi1 = self.indices[offset]
        vi2 = self.indices[offset + 1]
        vi3 = self.indices[offset + 2]
        return vi1, vi2, vi3

    def calculate_weighted_normals_for(self, triangles):
        """
        Calculates normal vectors for the specified triangles, this
        normal vectors are not normalized and multiplicated with the
        area of participating triangle
        :rtype: Array
        :param triangles:
        :return: Array of not normalized vectors [float,float,float]
        """
        weighted_normals = []
        for triangle in triangles:
            llh0 = self._uvh_to_llh(triangle[0])
            llh1 = self._uvh_to_llh(triangle[1])
            llh2 = self._uvh_to_llh(triangle[2])
            v0 = LLH2ECEF(llh0[0], llh0[1], llh0[2])
            v1 = LLH2ECEF(llh1[0], llh1[1], llh1[2])
            v2 = LLH2ECEF(llh2[0], llh2[1], llh2[2])

            normal = np.cross(c3d.subtract(v1, v0), c3d.subtract(v2, v0))
            area = triangleArea(v0, v1)
            weighted_normals.append(normal * area)

        return weighted_normals

    def toFile(self, file_path, gzipped=False):
        if self.is_index_dirty:
            self._rebuild_indices()

        super(EditableTerrainTile, self).toFile(file_path, gzipped)

    def fromFile(self, file_path, has_lighting=False, has_watermask=False, gzipped=False):
        self._file_path = file_path
        self._gzipped = gzipped

        super(EditableTerrainTile, self).fromFile(file_path, has_lighting, gzipped)

    def save(self):
        """
        persists the current state of the tile, no matter if changes were made,
        the old old state will be overwritten
        :return: void
        """
        target_dir_path = os.path.dirname(self._file_path)
        if not os.path.exists(target_dir_path):
            os.makedirs(target_dir_path)

        if os.path.exists(self._file_path):
            os.remove(self._file_path)

        self.toFile(self._file_path, self._gzipped)

    def save_to(self, target_dir_path, gzipped=False):
        """
        persists the current state of the tile into the specified directory path,
        if a tile with the same filename
        is existing, then the new file will overwrite these
        :param target_dir_path: the path to the directory
        :param gzipped: whether or not the terrain tile should be gzipped
        :return: void
        """
        tile_file_name = os.path.basename(self._file_path)
        if not os.path.exists(target_dir_path):
            os.makedirs(target_dir_path)

        file_path = os.path.join(target_dir_path, tile_file_name)
        if os.path.exists(file_path):
            os.remove(file_path)

        self.toFile(file_path, gzipped)

    def toWKT(self, file_path):
        """
        for debug use. persists the tile data as wkt data, all vertices and triangles
        will be create as WGS84 POINT Z and POLYGON Z WKT-Strings
        :param file_path: the file path where the wkt should be written
        :return:void
        """

        if self.is_index_dirty:
            self._rebuild_indices()

        with open(file_path, mode='w') as stream:
            vertices = self.getVerticesCoordinates()
            for i in range(len(vertices)):
                v = vertices[i]
                stream.write("POINT Z( {0} {1} {2}), {3}\n".format(v[0], v[1], v[2], i))

            indices = iter(self.indices)
            for i in range(0, len(self.indices) - 1, 3):
                vi1 = next(indices)
                vi2 = next(indices)
                vi3 = next(indices)
                llh1 = self._uvh_to_llh(vi1)
                llh2 = self._uvh_to_llh(vi2)
                llh3 = self._uvh_to_llh(vi3)
                v1_str = "{:.14f} {:.14f} {:.14f}".format(llh1[0], llh1[1], llh1[2])
                v2_str = "{:.14f} {:.14f} {:.14f}".format(llh2[0], llh2[1], llh2[2])
                v3_str = "{:.14f} {:.14f} {:.14f}".format(llh3[0], llh3[1], llh3[2])

                stream.write("POLYGON Z(( {0}, {1}, {2})), {3}\n".format(v1_str, v2_str,
                                                                         v3_str, i))

    def find_and_split_triangle(self, vertex_prev_index, vertex_next_index,
                                coordinate_vertex_new):
        """
        Finds and splits the triangle, specified by the vertex_prev_index and
        vertex_next_index into two new triangles with vertex_insert as new
        vertex of both triangles
        :param vertex_prev_index:the index of the previous vertex for the new vertex
        :param vertex_next_index:the index of the next vertex for the new vertex
        :param coordinate_vertex_new: the wgs84 coordinate of the vertex between
                vertex_prev and vertex_next
        :return: the index of the new vertex
        """

        triangle_index = self.find_triangle_of(vertex_prev_index, vertex_next_index)
        if triangle_index is None:
            raise Exception('No triangle found for Vertex')

        self.is_index_dirty = True
        old_triangle = list(self.get_triangle(triangle_index))
        new_triangle = list(old_triangle)

        longitude, latitude, height = coordinate_vertex_new
        u = self._quantize_longitude(longitude)
        v = self._quantize_latitude(latitude)

        # insert new vertex in u,v,h
        self.u.append(u)
        self.v.append(v)
        vertex_new_index = len(self.u) - 1

        if self.header['minimumHeight'] < height < self.header['maximumHeight']:
            if self._changed_heights:
                self._changed_heights.append(height)
            h = self._quantize_height(height)
        else:
            if not self._changed_heights:
                self._changed_heights = [self._dequantize_height(x) for x in self.h]
            self._changed_heights.append(height)
            h = 0

        self.h.append(h)
        self.vLight.append(null_normal)
        print("Adding new vertex ({0}) [lenght of vLight: {1}]".format(vertex_new_index,
                                                                       len(self.vLight)))

        # update triangle with new vertex index
        vertex_offset = old_triangle.index(vertex_next_index)
        old_triangle[vertex_offset] = vertex_new_index

        # create new triangle with 'vertex_insert'
        new_triangle[new_triangle.index(vertex_prev_index)] = vertex_new_index

        triangle_offset = (triangle_index * 3)
        # update old triangle in indices-Array
        self.indices[triangle_offset + vertex_offset] = vertex_new_index
        # add new triangle to indices-Array
        self.indices.extend(new_triangle)

        return vertex_new_index

    def rebuild_h(self):
        """
        Requantize the heights and sets min/max heights of this tile, if heights are
        changed, otherwise nothing will happens
        """
        if self._changed_heights:
            new_max = max(self._changed_heights)
            new_min = min(self._changed_heights)

            deniv = new_max - new_min
            b_height = old_div(MAX, deniv)
            for i in range(len(self._changed_heights)):
                changed_height = self._changed_heights[i]
                h = int(round((changed_height - new_min) * b_height))
                if h < 0:
                    h = 0
                if h > MAX:
                    h = MAX
                self.h[i] = h

            self.header['minimumHeight'] = new_min
            self.header['maximumHeight'] = new_max
            self._changed_heights = []

    def _rebuild_indices(self):
        """
        Private method, should only used internally if any edits
        on self.u, self.v, self.h  are made.
        """
        size = len(self.indices)
        new_u = []
        new_v = []
        new_h = []

        new_indices = []
        new_v_light = []
        index_map = {}

        new_index = 0
        for i in range(0, size):
            old_i = self.indices[i]

            if old_i in index_map.keys():
                new_i = index_map[old_i]
            else:
                index_map[old_i] = new_index
                new_i = new_index
                new_index += 1

                new_u.append(self.u[old_i])
                new_v.append(self.v[old_i])
                new_h.append(self.h[old_i])

                new_v_light.append(self.vLight[old_i])
            new_indices.append(new_i)

        if len(self.indices) == len(new_indices):
            self.indices = new_indices
        else:
            raise Exception("Array-Size of Indices not equal")

        if len(self.u) == len(new_u):
            self.u = new_u
        else:
            raise Exception("Array-Size of u-Values not equal")

        if len(self.v) == len(new_v):
            self.v = new_v
        else:
            raise Exception("Array-Size of v-Values not equal")

        if len(self.h) == len(new_h):
            self.h = new_h
        else:
            raise Exception("Array-Size of h-Values not equal")

        self.westI = self.get_edge_vertices('w')
        self.southI = self.get_edge_vertices('s')
        self.eastI = self.get_edge_vertices('e')
        self.northI = self.get_edge_vertices('n')

        self.vLight = new_v_light

    def _quantize_latitude(self, latitude):
        """
        Private helper method to convert latitude values to quantized tile (v) values
        :param latitude: the wgs 84 latitude in degrees
        :return: the quantized value (v)
        """
        b_lat = old_div(MAX, (self._north - self._south))
        v = int(round((latitude - self._south) * b_lat))
        return v

    def _quantize_longitude(self, longitude):
        """
        Private helper method to convert longitude values to quantized tile (u) values
        :param longitude: the wgs 84 longitude in degrees
        :return: the quantized value (u)
        """
        b_lon = old_div(MAX, (self._east - self._west))
        u = int(round((longitude - self._west) * b_lon))
        return u

    def _quantize_height(self, height):
        """
        Private helper method to convert height values to quantized tile (h) values
        :param height: the wgs 84 height in ground units (meter)
        :return: the quantized value (h)
        """
        deniv = self.header['maximumHeight'] - self.header['minimumHeight']
        # In case a tile is completely flat
        if deniv == 0:
            h = 0
        else:
            b_height = old_div(MAX, deniv)
            h = int(round((height - self.header['minimumHeight']) * b_height))
        return h

    def _dequantize_height(self, h):
        """
        Private helper method to convert quantized tile (h) values to real world height
        values
        :param h: the quantized height value
        :return: the height in ground units (meter)
        """
        return lerp(self.header['minimumHeight'],
                    self.header['maximumHeight'],
                    old_div(float(h), MAX))

    def _uvh_to_llh(self, index):
        """
        Private helper method to convert quantized tile vertex to wgs84 coordinate
        :param index: the index of the specified vertex
        :return: wgs84 coordinate
        """
        longitude = (lerp(self._west, self._east, old_div(float(self.u[index]), MAX)))
        latitude = (lerp(self._south, self._north, old_div(float(self.v[index]), MAX)))
        height = self._dequantize_height(self.h[index])
        return longitude, latitude, height
