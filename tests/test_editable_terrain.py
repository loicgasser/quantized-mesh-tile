# -*- coding: utf-8 -*-
import os
import platform
import unittest

from quantized_mesh_tile import tile_stitcher


def get_tmp_path():
    current_system = platform.system()
    if 'Windows' is current_system:
        return 'c:/Temp/'
    else:
        return '/tmp/'


def get_tile(z, x, y):
    terrain_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'data/%s_%s_%s.terrain' % (z, x, y))
    return tile_stitcher.load_tile(terrain_path, x, y, z)


class TestEditableTerrainTile(unittest.TestCase):

    def test_get_edge_coordinates(self):
        # arrange
        x = 17388
        y = 12517
        z = 14
        edge = 'w'

        # act
        tile = get_tile(z, x, y)
        coordinates = tile.get_edge_coordinates(edge)

        # assert
        self.assertTrue(len(coordinates) == 25)
        self.assertTrue(len(coordinates[0]) == 3)

    def test_toWKT(self):
        # arrange
        x = 17388
        y = 12517
        z = 14
        wkt_path = os.path.join(get_tmp_path(), 'test.wkt')

        try:
            # act
            tile = get_tile(z, x, y)
            tile.toWKT(wkt_path)
            # assert
            with open(wkt_path, mode='r') as wkt_file:
                lines = wkt_file.readlines()
            self.assertGreater(len(lines), 0)
        finally:
            os.remove(wkt_path)
