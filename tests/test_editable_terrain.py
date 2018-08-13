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

    def test_set_height_min(self):
        # arrange
        x = 17388
        y = 12517
        z = 14
        expected_height = 0

        # act
        tile = data_utils.build_terrain_tile(self.quantized_triangles, x, y, z)
        tile.set_height(0, -1.0)
        tile.rebuild_h()
        actual_height = tile.h[0]

        # assert
        self.assertEquals(actual_height, expected_height)

    def test_set_height_max(self):
        # arrange
        x = 17388
        y = 12517
        z = 14
        expected_height = 9999

        # act
        tile = data_utils.build_terrain_tile(self.quantized_triangles, x, y, z)
        tile.set_height(0, 9999)
        tile.rebuild_h()
        actual_height = tile.get_height(0)

        # assert
        self.assertEquals(actual_height, expected_height)

    def test_save_expected_exception(self):
        # arrange
        x = 17388
        y = 12517
        z = 14

        # act
        tile = data_utils.build_terrain_tile(self.quantized_triangles, x, y, z)

        # assert
        self.assertRaises(Exception, tile.save)

    def test_save_expected_existing_file(self):
        # arrange
        x = 17388
        y = 12517
        z = 14

        try:
            # act
            tile = data_utils.build_terrain_tile(self.quantized_triangles, x, y, z)
            test_path = os.path.join(data_utils.get_tmp_path(), "test.terrain")
            tile._file_path = test_path
            tile.save()

            # assert
            self.assertTrue(os.path.exists(test_path))
        finally:
            if os.path.exists(test_path):
                os.remove(test_path)
