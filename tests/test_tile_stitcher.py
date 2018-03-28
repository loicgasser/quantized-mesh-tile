# -*- coding: utf-8 -*-

import unittest

import os
import platform

from quantized_mesh_tile import TerrainTile
from quantized_mesh_tile.editable_terrain import EditableTerrainTile

from quantized_mesh_tile.global_geodetic import GlobalGeodetic
from quantized_mesh_tile.tile_stitcher import TileStitcher


class TestHarmonizeNormals(unittest.TestCase):
    def get_tmp_path(self):
        current_system = platform.system()
        if 'Windows' is current_system:
            return 'c:/Temp/'
        else:
            return '/tmp/'

    def get_tile(self, z, x, y):
        geodetic = GlobalGeodetic(True)
        [minx, miny, maxx, maxy] = geodetic.TileBounds(x, y, z)
        # print("{0}, {1}, {2},{3}".format(minx, miny, maxx, maxy))
        tile = EditableTerrainTile(west=minx, south=miny, east=maxx, north=maxy)
        tile.fromFile(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/%s_%s_%s.terrain' % (z, x, y)),
                      hasLighting=True)
        return tile

    def test_constructor(self):
        # arrange
        center_x = 17388
        center_y = 12517
        center_z = 14

        neighbour_x = 17388
        neighbour_y = 12518
        neighbour_z = 14

        # act
        center_tile = self.get_tile(center_z, center_x, center_y)
        neighbour_tile = self.get_tile(neighbour_z, neighbour_x, neighbour_y)
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
        center_tile = self.get_tile(center_z, center_x, center_y)
        neighbour_tile = self.get_tile(neighbour_z, neighbour_x, neighbour_y)
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

        center_tile = self.get_tile(center_z, center_x, center_y)
        neighbour_tile = self.get_tile(neighbour_z, neighbour_x, neighbour_y)

        # act
        stitcher = TileStitcher(center_tile)
        stitcher.stitch_with(neighbour_tile)

        with open(os.path.join(self.get_tmp_path(), '12_4347_3128.wkt'), mode='w') as f:
            center_tile.toWKT(f)

        with open(os.path.join(self.get_tmp_path(), '12_4347_3127.wkt'), mode='w') as f:
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

        center_tile = self.get_tile(center_z, center_x, center_y)
        neighbour_tile = self.get_tile(neighbour_z, neighbour_x, neighbour_y)

        # act
        stitcher = TileStitcher(center_tile)
        stitcher.stitch_with(neighbour_tile)

        center_tile.toFile(os.path.join(self.get_tmp_path(), '12_4347_3128.terrain'))
        neighbour_tile.toFile(os.path.join(self.get_tmp_path(), '12_4347_3127.terrain'))

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

        center_tile = self.get_tile(center_z, center_x, center_y)
        neighbour_tile = self.get_tile(neighbour_z, neighbour_x, neighbour_y)

        # act
        stitcher = TileStitcher(center_tile)
        stitcher.stitch_with(neighbour_tile)

        center_tile.toFile(os.path.join(self.get_tmp_path(), '12_4347_3128.terrain'))
        neighbour_tile.toFile(os.path.join(self.get_tmp_path(), '12_4348_3128.terrain'))

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

        center_tile = self.get_tile(center_z, center_x, center_y)
        east_tile = self.get_tile(east_z, east_x, east_y)
        south_tile = self.get_tile(south_z, south_x, south_y)

        # act
        stitcher = TileStitcher(center_tile)
        stitcher.add_neighbour(east_tile)
        stitcher.add_neighbour(south_tile)
        stitcher.stitch_together()

        center_tile.toFile(os.path.join(self.get_tmp_path(), '12_4346_3127.terrain'))
        east_tile.toFile(os.path.join(self.get_tmp_path(), '12_4347_3127.terrain'))
        south_tile.toFile(os.path.join(self.get_tmp_path(), '12_4346_3126.terrain'))

        # assert
        pass
