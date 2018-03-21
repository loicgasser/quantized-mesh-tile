# -*- coding: utf-8 -*-
import numpy as np
from future.utils import old_div

from quantized_mesh_tile import TerrainTile
from quantized_mesh_tile.terrain import MAX


class EditableTerrainTile(TerrainTile):

    def get_bounding_box(self):
        return {'west': self._west,
                'east': self._east,
                'north': self._north,
                'south': self._south}

    def set_normal(self, index, normal):
        current_size = len(self.vLight)
        if current_size <= index:
            diff = index - current_size
            temp = [[0, 0, 0] for i in range(diff+1)]
            self.vLight = self.vLight + temp
        self.vLight[index] = normal

    def set_height(self, index, height):
        self.h[index] = self.quantize_height(height)

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
        for i in xrange(0, len(self.indices) - 1, 3):
            vi1 = next(indices)
            vi2 = next(indices)
            vi3 = next(indices)
            triangle = (vi1, vi2, vi3)
            self._triangles.append(triangle)

    def split_triangle(self, triangle_index, vertex_prev_index, vertex_next_index, vertex_insert):
        old_triangle = list(self._triangles[triangle_index])
        new_triangle = list(old_triangle)

        # neuen Vertex von lat, lon, height in u,v, h umrechnen
        u_new, v_new, h_new = self.quantize_vertex(vertex_insert)

        # neuen Vertex hinzufügen in u,v,h
        self.u.append(u_new)
        self.v.append(v_new)
        self.h.append(h_new)

        vertex_new_index = len(self.h) - 1

        # Triangle mit neuem Vertex-Index aktualisieren
        old_triangle[old_triangle.index(vertex_next_index)] = vertex_new_index
        # neues Triangle mit vertex_insert bilden
        new_triangle[new_triangle.index(vertex_prev_index)] = vertex_new_index

        # neues triangle den Indices hinzufügen
        self.indices.extend(new_triangle)

        self._triangles[triangle_index] = old_triangle
        # neues triangle _triangles hinzufügen
        self._triangles.append(new_triangle)

        if len(self._longs) != 0:
            self._longs = []
            self._lats = []
            self._heights = []
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
