# -*- coding: utf-8 -*-

import unittest

import os

from quantized_mesh_tile import TerrainTile
from quantized_mesh_tile.editable_terrain import EditableTerrainTile

from quantized_mesh_tile.global_geodetic import GlobalGeodetic
from quantized_mesh_tile.tile_stitcher import TileStitcher


class TestHarmonizeNormals(unittest.TestCase):

    def get_tile(self, z, x, y):
        geodetic = GlobalGeodetic(True)
        [minx, miny, maxx, maxy] = geodetic.TileBounds(x, y, z)
        print("{0}, {1}, {2},{3}".format(minx, miny, maxx, maxy))
        tile = EditableTerrainTile(west=minx, south=miny, east=maxx, north=maxy)
        tile.fromFile(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/%s_%s_%s.terrain' % (z, x, y)),hasLighting=True)
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
        edge_connection = harmonizer.get_edge_connection(neighbour_tile)

        # assert
        self.assertIs(edge_connection, 'north')
        self.assertIsNotNone(edge_connection)

    def test_stitch_with(self):
        # arrange
        # center_x = 4347
        # center_y = 3127
        # center_z = 12
        #
        # neighbour_x = 4347
        # neighbour_y = 3126
        # neighbour_z = 12

        center_x = 4347
        center_y = 3126
        center_z = 12

        neighbour_x = 4346
        neighbour_y = 3126
        neighbour_z = 12

        center_tile = self.get_tile(center_z, center_x, center_y)
        neighbour_tile = self.get_tile(neighbour_z, neighbour_x, neighbour_y)

        # act
        stitcher = TileStitcher(center_tile)
        stitcher.stitch_with(neighbour_tile)

        center_tile.toFile('C:/Temp/12_4347_3126.terrain')
        neighbour_tile.toFile('C:/Temp/12_4346_3126.terrain')

        # with open('/tmp/12_4347_3126.obj', mode='w') as f:
        #     center_tile.write_to_obj(f)
        #
        # with open('/tmp/12_4346_3126.obj', mode='w') as f:
        #     neighbour_tile.write_to_obj(f)

        # assert
        pass

