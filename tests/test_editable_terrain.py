# -*- coding: utf-8 -*-
import os
import unittest
from tests import data_utils


class TestEditableTerrainTile(unittest.TestCase):
    def setUp(self):
        self.quantized_triangles = data_utils.read_quantized_triangles()

    def test_get_edge_coordinates(self):
        # arrange
        x = 17388
        y = 12517
        z = 14
        edge = 'w'

        # act
        tile = data_utils.build_terrain_tile(self.quantized_triangles, x, y, z)
        coordinates = tile.get_edge_coordinates(edge)

        # assert
        self.assertTrue(len(coordinates) == 2)
        self.assertTrue(len(coordinates[0]) == 3)

    def test_toWKT(self):
        # arrange
        x = 17388
        y = 12517
        z = 14
        wkt_path = os.path.join(data_utils.get_tmp_path(), 'test.wkt')

        try:
            # act
            tile = data_utils.build_terrain_tile(self.quantized_triangles, x, y, z)
            tile.toWKT(wkt_path)
            # assert
            with open(wkt_path, mode='r') as wkt_file:
                lines = wkt_file.readlines()
            self.assertGreater(len(lines), 0)
        finally:
            os.remove(wkt_path)
