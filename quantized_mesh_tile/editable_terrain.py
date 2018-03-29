# -*- coding: utf-8 -*-
import numpy as np
from future.utils import old_div

from quantized_mesh_tile import TerrainTile
from quantized_mesh_tile.llh_ecef import LLH2ECEF
from quantized_mesh_tile.terrain import MAX, lerp
from quantized_mesh_tile.utils import triangleArea
from . import cartesian3d as c3d

null_normal = [0, 0, 0]


class EditableTerrainTile(TerrainTile):

    def __init__(self, *args, **kwargs):
        super(EditableTerrainTile, self).__init__(*args, **kwargs)
        self.is_index_dirty = False

    def get_bounding_box(self):
        return {'west': self._west,
                'east': self._east,
                'north': self._north,
                'south': self._south}

    def set_normal(self, index, normal):
        self.is_index_dirty = True
        self.vLight[index] = normal

    def set_height(self, index, height):
        self.is_index_dirty = True
        self.h[index] = self._quantize_height(height)

    def get_height(self, index):
        height = self._dequantize_height(self.h[index])
        return height

    def get_llh(self, index):
        return self._uvh_to_llh(index)

    def find_triangle_of(self, vertex_prev, vertex_next):
        indices = iter(self.indices)
        triangles_prev = []
        triangles_next = []
        for i in range(0, len(self.indices), 3):
            vi1 = next(indices)
            vi2 = next(indices)
            vi3 = next(indices)
            triangle = (vi1, vi2, vi3)
            if vertex_prev in triangle:
                triangles_prev.append(i / 3)
            if vertex_next in triangle:
                triangles_next.append(i / 3)
        triangles = list(set(triangles_prev) - (set(triangles_prev) - set(triangles_next)))
        if len(triangles) == 0:
            return None

        return triangles[0]

    def find_all_triangles_of(self, vertex):
        triangles = []
        for triangle in self.get_triangles():
            if vertex in triangle:
                triangles.append(triangle)

        return triangles

    def get_triangles(self):
        indices = iter(self.indices)
        for i in range(0, len(self.indices), 3):
            vi1 = next(indices)
            vi2 = next(indices)
            vi3 = next(indices)
            triangle = (vi1, vi2, vi3)
            yield triangle

    def get_triangle(self, index):
        offset = index * 3

        vi1 = self.indices[offset]
        vi2 = self.indices[offset + 1]
        vi3 = self.indices[offset + 2]
        return vi1, vi2, vi3

    def calculate_weighted_normals_for(self, triangles):
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

    def toWKT(self, file_path):

        if self.is_index_dirty:
            self._rebuild_indices()

        with open(file_path, mode='w') as stream:
            for v in self.getVerticesCoordinates():
                stream.write("v {0} {1} {2}\n".format(v[0], v[1], v[2]))

            indices = iter(self.indices)
            for i in xrange(0, len(self.indices) - 1, 3):
                vi1 = next(indices)
                vi2 = next(indices)
                vi3 = next(indices)
                llh1 = self._uvh_to_llh(vi1)
                llh2 = self._uvh_to_llh(vi2)
                llh3 = self._uvh_to_llh(vi3)
                v1_str = "{:.14f} {:.14f} {:.14f}".format(llh1[0], llh1[1], llh1[2])
                v2_str = "{:.14f} {:.14f} {:.14f}".format(llh2[0], llh2[1], llh2[2])
                v3_str = "{:.14f} {:.14f} {:.14f}".format(llh3[0], llh3[1], llh3[2])

                stream.write("POLYGON Z(( {0}, {1}, {2}))\n".format(v1_str, v2_str, v3_str))

    def split_triangle(self, triangle_index, vertex_prev_index, vertex_next_index, vertex_insert):
        self.is_index_dirty = True
        old_triangle = list(self.get_triangle(triangle_index))
        new_triangle = list(old_triangle)

        longitude, latitude, height = vertex_insert
        u = self._quantize_longitude(longitude)
        v = self._quantize_latitude(latitude)
        h = self._quantize_height(height)

        # insert new vertex in u,v,h
        self.u.append(u)
        self.v.append(v)
        self.h.append(h)
        self.vLight.append(null_normal)

        vertex_new_index = len(self.h) - 1

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

    def _rebuild_indices(self):
        size = len(self.indices)
        new_u = []
        new_v = []
        new_h = []

        new_indices = []
        new_west_i = []
        new_south_i = []
        new_east_i = []
        new_north_i = []

        new_v_light = []
        index_map = {}

        new_index = 0
        for i in xrange(0, size):
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

                if old_i in self.westI:
                    new_west_i.append(new_i)

                if old_i in self.southI:
                    new_south_i.append(new_i)

                if old_i in self.eastI:
                    new_east_i.append(new_i)

                if old_i in self.northI:
                    new_north_i.append(new_i)

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

        if len(self.westI) == len(new_west_i):
            self.westI = new_west_i
        else:
            raise Exception("Array-Size of westIndices not equal")

        if len(self.southI) == len(new_south_i):
            self.southI = new_south_i
        else:
            raise Exception("Array-Size of southIndices not equal")

        if len(self.eastI) == len(new_east_i):
            self.eastI = new_east_i
        else:
            raise Exception("Array-Size of eastIndices not equal")

        if len(self.northI) == len(new_north_i):
            self.northI = new_north_i
        else:
            raise Exception("Array-Size of northIndices not equal")

        if len(self.vLight) == len(new_v_light):
            self.vLight = new_v_light
        else:
            raise Exception("Array-Size of northIndices not equal")

    def _quantize_latitude(self, latitude):
        b_lat = old_div(MAX, (self._north - self._south))
        v = int(round((latitude - self._south) * b_lat))
        return v

    def _quantize_longitude(self, longitude):
        b_lon = old_div(MAX, (self._east - self._west))
        u = int(round((longitude - self._west) * b_lon))
        return u

    def _quantize_height(self, height):
        deniv = self.header['maximumHeight'] - self.header['minimumHeight']
        # In case a tile is completely flat
        if deniv == 0:
            h = 0
        else:
            b_height = old_div(MAX, deniv)
            h = int(round((height - self.header['minimumHeight']) * b_height))
        return h

    def _dequantize_height(self, h):
        return lerp(self.header['minimumHeight'], self.header['maximumHeight'], old_div(float(h), MAX))

    def _uvh_to_llh(self, index):
        long = (lerp(self._west, self._east, old_div(float(self.u[index]), MAX)))
        lat = (lerp(self._south, self._north, old_div(float(self.v[index]), MAX)))
        height = self._dequantize_height(self.h[index])
        return long, lat, height