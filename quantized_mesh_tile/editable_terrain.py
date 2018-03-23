# -*- coding: utf-8 -*-
import numpy as np
from future.utils import old_div
from quantized_mesh_tile.utils import triangleArea

from quantized_mesh_tile.llh_ecef import LLH2ECEF

from quantized_mesh_tile import TerrainTile
from quantized_mesh_tile.terrain import MAX, lerp
from . import cartesian3d as c3d

null_normal = [0, 0, 0]


class EditableTerrainTile(TerrainTile):

    def __init__(self, *args, **kwargs):
        super(EditableTerrainTile, self).__init__(*args, **kwargs)

    def get_bounding_box(self):
        return {'west': self._west,
                'east': self._east,
                'north': self._north,
                'south': self._south}

    def set_normal(self, index, normal):
        self.vLight[index] = normal

    def set_h(self, index, h):
        self.h[index] = h

    def set_height(self, index, height):
        self.h[index] = self.quantize_height(height)

    def get_uvh(self, index):
        return self.u[index], self.v[index], self.h[index]

    def find_triangle_of(self, vertex_prev, vertex_next):
        if not self._triangles:
            self.build_triangles()

        for triangle in self._triangles:
            if vertex_prev in triangle and vertex_next in triangle:
                return self._triangles.index(triangle)
        return None

    def find_all_triangles_of(self, vertex):
        triangles = []
        if not self._triangles:
            self.build_triangles()

        for triangle in self._triangles:
            if vertex in triangle:
                triangles.append(triangle)

        return triangles

    def build_triangles(self):
        indices = iter(self.indices)
        for i in range(0, len(self.indices) - 1, 3):
            vi1 = next(indices)
            vi2 = next(indices)
            vi3 = next(indices)
            triangle = (vi1, vi2, vi3)
            self._triangles.append(triangle)

    def split_triangle(self, triangle_index, vertex_prev_index, vertex_next_index, vertex_insert):

        old_triangle = list(self._triangles[triangle_index])
        new_triangle = list(old_triangle)

        u, v, h = vertex_insert

        # insert new vertex in u,v,h
        self.u.append(u)
        self.v.append(v)
        self.h.append(h)
        self.vLight.append(null_normal)

        vertex_new_index = len(self.h) - 1

        # update triangle with new vertex index
        old_triangle[old_triangle.index(vertex_next_index)] = vertex_new_index
        # create new triangle with 'vertex_insert'
        new_triangle[new_triangle.index(vertex_prev_index)] = vertex_new_index

        # add new triangle to indices-Array
        self.indices.extend(new_triangle)

        self._triangles[triangle_index] = old_triangle
        self._triangles.append(new_triangle)

        return vertex_new_index

    def quantize_vertex(self, vertex):
        u = self.quantize_longitude(vertex[0])
        v = self.quantize_latitude(vertex[1])
        h = self.quantize_height(vertex[2])

        return u, v, h

    def quantize_latitude(self, latitude):
        b_lat = old_div(MAX, (self._north - self._south))
        v = int(round((latitude - self._south) * b_lat))
        return v

    def quantize_longitude(self, longitude):
        b_lon = old_div(MAX, (self._east - self._west))
        u = int(round((longitude - self._west) * b_lon))
        return u

    def quantize_height(self, height):
        deniv = self.header['maximumHeight'] - self.header['minimumHeight']
        # In case a tile is completely flat
        if deniv == 0:
            h = 0
        else:
            b_height = old_div(MAX, deniv)
            h = int(round((height - self.header['minimumHeight']) * b_height))
        return h

    def calculate_normals_for(self, triangles):
        weighted_normals = []
        for triangle in triangles:
            llh0 = self.uvh2_to_llh(triangle[0])
            llh1 = self.uvh2_to_llh(triangle[1])
            llh2 = self.uvh2_to_llh(triangle[2])
            v0 = LLH2ECEF(llh0[0],llh0[1],llh0[2])
            v1 = LLH2ECEF(llh1[0],llh1[1],llh1[2])
            v2 = LLH2ECEF(llh2[0],llh2[1],llh2[2])

            normal = np.cross(c3d.subtract(v1, v0), c3d.subtract(v2, v0))
            area = triangleArea(v0, v1)

            weighted_normals.append(normal * area)
        return weighted_normals

    def uvh2_to_llh(self, index):
        long = (lerp(self._west, self._east, old_div(float(self.u[index]), MAX)))
        lat = (lerp(self._south, self._north, old_div(float(self.v[index]), MAX)))
        height = (
            lerp(
                self.header['minimumHeight'],
                self.header['maximumHeight'],
                old_div(float(self.h[index]), MAX)
            )
        )
        return long, lat, height
