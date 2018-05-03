# -*- coding: utf-8 -*-
import unittest
import os
import platform

from quantized_mesh_tile import TerrainTile
from quantized_mesh_tile.editable_terrain import EditableTerrainTile

from quantized_mesh_tile.global_geodetic import GlobalGeodetic
from quantized_mesh_tile.tile_stitcher import TileStitcher


def get_neighbours(z, x, y):
    return {'west': (z, x - 1, y),
            'north': (z, x, y + 1),
            'south': (z, x, y - 1),
            'east': (z, x + 1, y)}


def get_neighbours_south_east(z, x, y):
    return {'south': (z, x, y - 1),
            'east': (z, x + 1, y)}


def get_tmp_path():
    current_system = platform.system()
    if 'Windows' is current_system:
        return 'c:/Temp/'
    else:
        return '/tmp/'


def load_tile(terrain_path, x, y, z):
    """

    :rtype: EditableTerrainTile
    """
    geodetic = GlobalGeodetic(True)
    [minx, miny, maxx, maxy] = geodetic.TileBounds(x, y, z)
    tile = EditableTerrainTile(west=minx, south=miny, east=maxx, north=maxy)
    tile.fromFile(terrain_path, has_lighting=True)
    return tile


def get_tile(z, x, y):
    terrain_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/%s_%s_%s.terrain' % (z, x, y))
    return load_tile(terrain_path, x, y, z)


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
        stitcher = TileStitcher(center_tile)

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
        center_tile = load_tile(os.path.join(get_tmp_path(), '12_4347_3128.terrain'),
                                center_x,
                                center_y,
                                center_z)
        neighbour_tile = load_tile(os.path.join(get_tmp_path(), '12_4347_3127.terrain'),
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

    def itest_traverse_over_directory_and_stitch(self):
        # arrange

        directory_base_path = '/export/home/schle_th/github/cesium/TestData/terrain_n/'
        # directory_base_path = 'C:/Work/terrain/'
        levels = [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
        # levels = [15]

        # act
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
                center_tile = load_tile(tile_path, x, y, level)

                stitcher = TileStitcher(center_tile, tile_path)
                for n, tile_info in neighbours.items():
                    n_z, n_x, n_y = tile_info

                    neighbour_path = os.path.join(directory_path, '%s/%s.terrain' % (n_x, n_y))
                    if os.path.exists(neighbour_path):
                        print("\tadding Neighbour {0}...".format(neighbour_path))
                        tile = load_tile(neighbour_path, n_x, n_y, level)
                        stitcher.add_neighbour(tile, neighbour_path)
                stitcher.stitch_together()
                stitcher.save()
