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
    geodetic = GlobalGeodetic(True)
    [minx, miny, maxx, maxy] = geodetic.TileBounds(x, y, z)
    tile = EditableTerrainTile(west=minx, south=miny, east=maxx, north=maxy)
    tile.fromFile(terrain_path, hasLighting=True)
    return tile


def get_tile(z, x, y):
    terrain_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/%s_%s_%s.terrain' % (z, x, y))
    return load_tile(terrain_path, x, y, z)


class TestHarmonizeNormals(unittest.TestCase):

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
        harmonizer = TileStitcher(center_tile)
        edge_connection = harmonizer._get_edge_connection(neighbour_tile)

        # assert
        self.assertIs(edge_connection, 'north')
        self.assertIsNotNone(edge_connection)

    def test_stitch_with_to_wkt(self):
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
        stitcher.stitch_with(neighbour_tile)

        with open(os.path.join(get_tmp_path(), '12_4347_3128.wkt'), mode='w') as f:
            center_tile.toWKT(f)

        with open(os.path.join(get_tmp_path(), '12_4347_3127.wkt'), mode='w') as f:
            neighbour_tile.toWKT(f)

        # assert
        pass

    def test_stitch_with_north_south(self):
        # arrange
        center_x = 4347
        center_y = 3128
        center_z = 12

        neighbour_x = 4347
        neighbour_y = 3127
        neighbour_z = 12

        center_tile = get_tile(center_z, center_x, center_y)
        neighbour_tile = get_tile(neighbour_z, neighbour_x, neighbour_y)
        if os.path.exists(os.path.join(get_tmp_path(), 'before_12_4347_3128.wkt')):
            os.remove(os.path.join(get_tmp_path(), 'before_12_4347_3128.wkt'))
        center_tile.toWKT(os.path.join(get_tmp_path(), 'before_12_4347_3128.wkt'))
        if os.path.exists(os.path.join(get_tmp_path(), 'before_12_4347_3127.wkt')):
            os.remove(os.path.join(get_tmp_path(), 'before_12_4347_3127.wkt'))
        neighbour_tile.toWKT(os.path.join(get_tmp_path(), 'before_12_4347_3127.wkt'))

        # act
        stitcher = TileStitcher(center_tile)
        stitcher.add_neighbour(neighbour_tile)
        stitcher.stitch_together()

        if os.path.exists(os.path.join(get_tmp_path(), '12_4347_3128.terrain')):
            os.remove(os.path.join(get_tmp_path(), '12_4347_3128.terrain'))
        center_tile.toFile(os.path.join(get_tmp_path(), '12_4347_3128.terrain'))

        if os.path.exists(os.path.join(get_tmp_path(), '12_4347_3127.terrain')):
            os.remove(os.path.join(get_tmp_path(), '12_4347_3127.terrain'))
        neighbour_tile.toFile(os.path.join(get_tmp_path(), '12_4347_3127.terrain'))

        center_tile = load_tile(os.path.join(get_tmp_path(), '12_4347_3128.terrain'), center_x, center_y, center_z)
        neighbour_tile = load_tile(os.path.join(get_tmp_path(), '12_4347_3127.terrain'), neighbour_x, neighbour_y,
                                   neighbour_z)

        if os.path.exists(os.path.join(get_tmp_path(), '12_4347_3128.wkt')):
            os.remove(os.path.join(get_tmp_path(), '12_4347_3128.wkt'))
        center_tile.toWKT(os.path.join(get_tmp_path(), '12_4347_3128.wkt'))
        if os.path.exists(os.path.join(get_tmp_path(), '12_4347_3127.wkt')):
            os.remove(os.path.join(get_tmp_path(), '12_4347_3127.wkt'))
        neighbour_tile.toWKT(os.path.join(get_tmp_path(), '12_4347_3127.wkt'))

        # assert
        pass

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

        if os.path.exists(os.path.join(get_tmp_path(), '12_4347_3128.terrain')):
            os.remove(os.path.join(get_tmp_path(), '12_4347_3128.terrain'))
        center_tile.toFile(os.path.join(get_tmp_path(), '12_4347_3128.terrain'))

        if os.path.exists(os.path.join(get_tmp_path(), '12_4348_3128.terrain')):
            os.remove(os.path.join(get_tmp_path(), '12_4348_3128.terrain'))
        neighbour_tile.toFile(os.path.join(get_tmp_path(), '12_4348_3128.terrain'))

        # assert
        pass

    def test_debug_toWKT(self):

        # arrange
        center_x = 4344
        center_y = 3124
        center_z = 12

        east_x = 4347
        east_y = 3127
        east_z = 12

        # act
        # east_tile = get_tile(east_z, east_x, east_y)
        center_tile = load_tile('C:/Work/terrain/12_/4344/3124.terrain', center_x, center_y, center_z)
        stitcher = TileStitcher(center_tile)

        if os.path.exists(os.path.join(get_tmp_path(), '12_4344_3124.wkt')):
            os.remove(os.path.join(get_tmp_path(), '12_4344_3124.wkt'))
        center_tile.toWKT(os.path.join(get_tmp_path(), '12_4344_3124.wkt'))
        # assert
        pass

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

        if os.path.exists(os.path.join(get_tmp_path(), '12_4346_3127.terrain')):
            os.remove(os.path.join(get_tmp_path(), '12_4346_3127.terrain'))
        center_tile.toFile(os.path.join(get_tmp_path(), '12_4346_3127.terrain'))
        if os.path.exists(os.path.join(get_tmp_path(), '12_4347_3127.terrain')):
            os.remove(os.path.join(get_tmp_path(), '12_4347_3127.terrain'))
        east_tile.toFile(os.path.join(get_tmp_path(), '12_4347_3127.terrain'))
        if os.path.exists(os.path.join(get_tmp_path(), '12_4346_3126.terrain')):
            os.remove(os.path.join(get_tmp_path(), '12_4346_3126.terrain'))
        south_tile.toFile(os.path.join(get_tmp_path(), '12_4346_3126.terrain'))

        # assert
        pass

    def test_stitch_from_local_filesystem(self):
        # arrange
        level = 15
        directory_base_path = 'C:/Work/terrain/'
        directory_path = os.path.join(directory_base_path, str(level) + '_')
        tile_path = 'C:/Work/terrain/15_/34762/25021.terrain'

        y = int(os.path.basename(tile_path).split('.')[0])
        x = int(os.path.basename(os.path.dirname(tile_path)))
        print('processing {0} ...'.format(tile_path))
        neighbours = get_neighbours_south_east(level, x, y)
        center_tile = load_tile(tile_path, x, y, level)

        stitcher = TileStitcher(center_tile)
        for n, tile_info in neighbours.items():
            n_z, n_x, n_y = tile_info

            neighbour_path = os.path.join(directory_path, '%s/%s.terrain' % (n_x, n_y))
            if os.path.exists(neighbour_path):
                print("\tadding Neighbour {0}...".format(neighbour_path))
                tile = load_tile(neighbour_path, n_x, n_y, level)
                stitcher.add_neighbour(tile)
        result_path = tile_path.replace('/{0}_'.format(level), '/edited_{0}'.format(level))
        stitcher.stitch_together()
        target_dir_path = os.path.dirname(result_path)
        if not os.path.exists(target_dir_path):
            os.makedirs(target_dir_path)

        if os.path.exists(result_path):
            os.remove(result_path)
        center_tile.toFile(result_path)

    def test_traverse_over_directory(self):
        # arrange
        # 15_\34762\25021
        # directory_base_path = '/export/data1/Test_DGMNormals/'
        directory_base_path = 'C:/Work/terrain/'
        levels = [12, 13, 14, 15, 16]

        # act
        for level in levels:
            directory_path = os.path.join(directory_base_path, str(level) + '_')
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

                stitcher = TileStitcher(center_tile)
                for n, tile_info in neighbours.items():
                    n_z, n_x, n_y = tile_info

                    neighbour_path = os.path.join(directory_path, '%s/%s.terrain' % (n_x, n_y))
                    if os.path.exists(neighbour_path):
                        print("\tadding Neighbour {0}...".format(neighbour_path))
                        tile = load_tile(neighbour_path, n_x, n_y, level)
                        stitcher.add_neighbour(tile)
                result_path = tile_path.replace('/{0}_'.format(level), '/edited_{0}'.format(level))
                stitcher.stitch_together()
                target_dir_path = os.path.dirname(result_path)
                if not os.path.exists(target_dir_path):
                    os.makedirs(target_dir_path)

                if os.path.exists(result_path):
                    os.remove(result_path)
                center_tile.toFile(result_path)
