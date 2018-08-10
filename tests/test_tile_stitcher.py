# -*- coding: utf-8 -*-
import os
import unittest

from quantized_mesh_tile import TerrainTile, tile_stitcher
from quantized_mesh_tile.tile_stitcher import TileStitcher, EdgeConnection
from tests import data_utils


class TestTileStitcher(unittest.TestCase):

    def setUp(self):
        self.quantized_triangles = data_utils.read_quantized_triangles()

    def test_constructor(self):
        # arrange
        center_x = 17388
        center_y = 12517
        center_z = 14

        neighbour_x = 17388
        neighbour_y = 12518
        neighbour_z = 14

        # act
        center_tile = data_utils.build_terrain_tile(self.quantized_triangles, center_x, center_y, center_z)
        neighbour_tile = data_utils.build_terrain_tile(self.quantized_triangles, neighbour_x, neighbour_y, neighbour_z)
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
        center_tile = data_utils.build_terrain_tile(self.quantized_triangles, center_x, center_y, center_z)
        neighbour_tile = data_utils.build_terrain_tile(self.quantized_triangles, neighbour_x, neighbour_y, neighbour_z)
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

        center_tile = data_utils.build_terrain_tile(self.quantized_triangles, center_x, center_y, center_z)
        neighbour_tile = data_utils.build_terrain_tile(self.quantized_triangles, neighbour_x, neighbour_y, neighbour_z)

        # act
        stitcher = TileStitcher(center_tile)
        stitcher.add_neighbour(neighbour_tile)
        stitcher.stitch_together()
        stitcher.save_to(data_utils.get_tmp_path())

        # assert
        center_tile = tile_stitcher.load_tile(
            os.path.join(data_utils.get_tmp_path(), '12_4347_3128.terrain'),
            center_x,
            center_y,
            center_z)
        neighbour_tile = tile_stitcher.load_tile(
            os.path.join(data_utils.get_tmp_path(), '12_4347_3127.terrain'),
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

        center_tile = data_utils.build_terrain_tile(self.quantized_triangles, center_x, center_y, center_z)
        neighbour_tile = data_utils.build_terrain_tile(self.quantized_triangles, neighbour_x, neighbour_y, neighbour_z)

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

        center_tile = data_utils.build_terrain_tile(self.quantized_triangles, center_x, center_y, center_z)
        east_tile = data_utils.build_terrain_tile(self.quantized_triangles, east_x, east_y, east_z)
        south_tile = data_utils.build_terrain_tile(self.quantized_triangles, south_x, south_y, south_z)

        # act
        stitcher = TileStitcher(center_tile)
        stitcher.add_neighbour(east_tile)
        stitcher.add_neighbour(south_tile)
        stitcher.stitch_together()
        stitcher.save_to(data_utils.get_tmp_path())

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

        center_tile = data_utils.build_terrain_tile(self.quantized_triangles, center_x, center_y, center_z)
        east_tile = data_utils.build_terrain_tile(self.quantized_triangles, east_x, east_y, east_z)
        south_tile = data_utils.build_terrain_tile(self.quantized_triangles, south_x, south_y, south_z)

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

    def test_harmonize_with_east_and_south(self):
        # arrange
        expected_changes = 71
        center_x = 67
        center_y = 49
        center_z = 6

        east_x = 68
        east_y = 49
        east_z = 6

        south_x = 67
        south_y = 48
        south_z = 6

        center_tile = data_utils.get_tile(center_z, center_x, center_y)
        east_tile = data_utils.get_tile(east_z, east_x, east_y)
        south_tile = data_utils.get_tile(south_z, south_x, south_y)
        normal_vectors_before = list(center_tile.vLight)

        # act
        stitcher = TileStitcher(center_tile)
        stitcher.add_neighbour(east_tile)
        stitcher.add_neighbour(south_tile)
        stitcher.harmonize_normals()
        normal_vectors_after = list(center_tile.vLight)

        # assert
        changes = []
        for i, normal in enumerate(normal_vectors_before):
            normal_before = set(normal)
            normal_after = set(normal_vectors_after[i])
            changed = normal_before.difference(normal_after)
            if changed:
                changes.append(i)

        actual_changes = len(changes)
        self.assertTrue(actual_changes == expected_changes)

    def test_get_neighbours(self):
        # arrange
        center_x = 17380
        center_y = 12516
        center_z = 14

        expected_west = [14, 17379, 12516]
        expected_north = [14, 17380, 12517]
        expected_east = [14, 17381, 12516]
        expected_south = [14, 17380, 12515]

        # act
        neighbours = tile_stitcher.get_neighbours(center_z, center_x, center_y)

        # assert
        self.assertSequenceEqual(neighbours['west'], expected_west)
        self.assertSequenceEqual(neighbours['north'], expected_north)
        self.assertSequenceEqual(neighbours['east'], expected_east)
        self.assertSequenceEqual(neighbours['south'], expected_south)

    def test_get_neighbours_south_east(self):
        # arrange
        center_x = 17380
        center_y = 12516
        center_z = 14

        expected_east = [14, 17381, 12516]
        expected_south = [14, 17380, 12515]

        # act
        neighbours = tile_stitcher.get_neighbours_south_east(center_z, center_x, center_y)

        # assert
        self.assertSequenceEqual(neighbours['east'], expected_east)
        self.assertSequenceEqual(neighbours['south'], expected_south)

    def test_EdgeConnection_repr(self):
        # arrange
        expected_repr_start = 'E:w [1] -> ({'

        # act
        ec = EdgeConnection('w', 1)
        ec.add_side('w', 2)
        ec.add_side('c', 3)
        actual_repr = ec.__repr__()

        # assert
        self.assertTrue(actual_repr.startswith(expected_repr_start))
