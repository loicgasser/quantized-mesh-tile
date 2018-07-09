# -*- coding: utf-8 -*-
import os
import platform
import unittest

from quantized_mesh_tile import TerrainTile, tile_stitcher
from quantized_mesh_tile.tile_stitcher import TileStitcher


def get_neighbours(z, x, y):
    return {'west': (z, x - 1, y),
            'north': (z, x, y + 1),
            'south': (z, x, y - 1),
            'east': (z, x + 1, y)}


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


class TestTileStitcher(unittest.TestCase):

    def test_constructor(self):
        # arrange
        center_x = 17388
        center_y = 12517
        center_z = 14

        neighbour_x = 17388
        neighbour_y = 12518
        neighbour_z = 14

        # act
        center_tile = get_tile(center_z, center_x, center_y)
        neighbour_tile = get_tile(neighbour_z, neighbour_x, neighbour_y)
        TileStitcher(center_tile)

        # assert
        self.assertIsInstance(center_tile, TerrainTile)
        self.assertIsInstance(neighbour_tile, TerrainTile)

    def test_getEdgeConnection(self):
        # arrange
        center_x = 17388
        center_y = 12517
        center_z = 14

        neighbour_x = 17388
        neighbour_y = 12518
        neighbour_z = 14

        # act
        center_tile = get_tile(center_z, center_x, center_y)
        neighbour_tile = get_tile(neighbour_z, neighbour_x, neighbour_y)
        stitcher = TileStitcher(center_tile)
        edge_connection = stitcher._get_edge_connection(neighbour_tile)

        # assert
        self.assertIs(edge_connection, 'n')
        self.assertIsNotNone(edge_connection)

    def test_stitch_together_with_south(self):
        # arrange
        center_x = 4347
        center_y = 3128
        center_z = 12

        neighbour_x = 4347
        neighbour_y = 3127
        neighbour_z = 12

        center_tile = get_tile(center_z, center_x, center_y)
        neighbour_tile = get_tile(neighbour_z, neighbour_x, neighbour_y)

        # act
        stitcher = TileStitcher(center_tile)
        stitcher.add_neighbour(neighbour_tile)
        stitcher.stitch_together()
        stitcher.save_to(get_tmp_path())

        # assert
        center_tile = tile_stitcher.load_tile(
            os.path.join(get_tmp_path(), '12_4347_3128.terrain'),
            center_x,
            center_y,
            center_z)
        neighbour_tile = tile_stitcher.load_tile(
            os.path.join(get_tmp_path(), '12_4347_3127.terrain'),
            neighbour_x,
            neighbour_y,
            neighbour_z)

        center_vertices_count = len(center_tile.get_edge_vertices(edge='s'))
        neighbour_vertices_count = len(neighbour_tile.get_edge_vertices(edge='n'))

        self.assertTrue(center_vertices_count == neighbour_vertices_count)

    def test_stitch_with_west_east(self):
        # arrange
        center_x = 4347
        center_y = 3128
        center_z = 12

        neighbour_x = 4348
        neighbour_y = 3128
        neighbour_z = 12

        center_tile = get_tile(center_z, center_x, center_y)
        neighbour_tile = get_tile(neighbour_z, neighbour_x, neighbour_y)

        # act
        stitcher = TileStitcher(center_tile)
        stitcher.add_neighbour(neighbour_tile)
        stitcher.stitch_together()

        # assert
        center_vertices_count = len(center_tile.get_edge_vertices(edge='e'))
        neighbour_vertices_count = len(neighbour_tile.get_edge_vertices(edge='w'))
        self.assertTrue(center_vertices_count == neighbour_vertices_count)

    def test_stitch_with_east_and_south(self):
        # arrange
        center_x = 4346
        center_y = 3127
        center_z = 12

        east_x = 4347
        east_y = 3127
        east_z = 12

        south_x = 4346
        south_y = 3126
        south_z = 12

        center_tile = get_tile(center_z, center_x, center_y)
        east_tile = get_tile(east_z, east_x, east_y)
        south_tile = get_tile(south_z, south_x, south_y)

        # act
        stitcher = TileStitcher(center_tile)
        stitcher.add_neighbour(east_tile)
        stitcher.add_neighbour(south_tile)
        stitcher.stitch_together()

        # assert
        center_to_east_vertices_count = len(center_tile.get_edge_vertices(edge='e'))
        center_to_south_vertices_count = len(center_tile.get_edge_vertices(edge='s'))
        east_vertices_count = len(east_tile.get_edge_vertices(edge='w'))
        south_vertices_count = len(south_tile.get_edge_vertices(edge='n'))

        self.assertTrue(center_to_east_vertices_count == east_vertices_count)
        self.assertTrue(center_to_south_vertices_count == south_vertices_count)

    def test_stitch_with_east_and_south_z14x17380y12516(self):
        # arrange
        center_x = 17380
        center_y = 12516
        center_z = 14

        east_x = 17381
        east_y = 12516
        east_z = 14

        south_x = 17380
        south_y = 12515
        south_z = 14

        center_tile = get_tile(center_z, center_x, center_y)
        east_tile = get_tile(east_z, east_x, east_y)
        south_tile = get_tile(south_z, south_x, south_y)

        # act
        stitcher = TileStitcher(center_tile)
        stitcher.add_neighbour(east_tile)
        stitcher.add_neighbour(south_tile)
        stitcher.stitch_together()

        # assert
        center_to_east_vertices_count = len(center_tile.get_edge_vertices(edge='e'))
        center_to_south_vertices_count = len(center_tile.get_edge_vertices(edge='s'))
        east_vertices_count = len(east_tile.get_edge_vertices(edge='w'))
        south_vertices_count = len(south_tile.get_edge_vertices(edge='n'))

        self.assertTrue(center_to_east_vertices_count == east_vertices_count)
        self.assertTrue(center_to_south_vertices_count == south_vertices_count)
