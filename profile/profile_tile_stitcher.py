# -*- coding: utf-8 -*-
import os
import platform
import cProfile

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
                                '../tests/data/%s_%s_%s.terrain' % (z, x, y))
    return tile_stitcher.load_tile(terrain_path, x, y, z)

def profile_stitch_together_with_south():
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

def profile_stitch_with_east_and_south():
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


cProfile.run('profile_stitch_together_with_south()',sort='calls')
