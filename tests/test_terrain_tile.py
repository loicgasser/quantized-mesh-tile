# -*- coding: utf-8 -*-

from future import standard_library

standard_library.install_aliases()
from builtins import range
import os
import unittest
import io
from quantized_mesh_tile.terrain import TerrainTile
from quantized_mesh_tile.topology import TerrainTopology
from quantized_mesh_tile.global_geodetic import GlobalGeodetic


class TestTerrainTile(unittest.TestCase):
    def setUp(self):
        self.tmpfile = 'tests/data/temp.terrain'

    def tearDown(self):
        if os.path.exists(self.tmpfile):
            os.remove(self.tmpfile)

    def testReaderWriter(self):
        '''
        Circle jerk testing.
        We read the file with our reader
        We write this data with our writer to a temporary file
        We read this temporary file
        We compare the results
        '''
        x = 533
        y = 383
        z = 9
        geodetic = GlobalGeodetic(True)
        [minx, miny, maxx, maxy] = geodetic.TileBounds(x, y, z)

        ter = TerrainTile(west=minx, south=miny, east=maxx, north=maxy)
        ter.fromFile('tests/data/%s_%s_%s.terrain' % (z, x, y))
        ter.toFile(self.tmpfile)
        self.assertIsInstance(ter.__repr__(), str)

        ter2 = TerrainTile(west=minx, south=miny, east=maxx, north=maxy)
        ter2.fromFile(self.tmpfile)
        self.assertIsInstance(ter2.__repr__(), str)

        # check headers
        self.assertGreater(len(ter.header), 0)
        self.assertEqual(len(ter.header), len(ter2.header))
        self.assertEqual(len(ter.header), len(TerrainTile.quantizedMeshHeader))
        for k, v in ter.header.items():
            self.assertEqual(v, ter2.header[k], 'For k = ' + k)

        # check vertices
        self.assertGreater(len(ter.u), 0)
        self.assertGreater(len(ter.v), 0)
        self.assertGreater(len(ter.h), 0)
        self.assertEqual(len(ter.u), len(ter2.u))
        self.assertEqual(len(ter.v), len(ter2.v))
        self.assertEqual(len(ter.h), len(ter2.h))
        for i, v in enumerate(ter.u):
            self.assertEqual(v, ter2.u[i])
        for i, v in enumerate(ter.v):
            self.assertEqual(v, ter2.v[i])
        for i, v in enumerate(ter.h):
            self.assertEqual(v, ter2.h[i])
        self.assertEqual(
            len(ter.getVerticesCoordinates()),
            len(ter2.getVerticesCoordinates())
        )

        # check indices
        self.assertGreater(len(ter.indices), 0)
        self.assertEqual(len(ter.indices), len(ter2.indices))
        for i, v in enumerate(ter.indices):
            self.assertEqual(v, ter2.indices[i], i)

        # check edges
        self.assertGreater(len(ter.westI), 0)
        self.assertEqual(len(ter.westI), len(ter2.westI))
        for i, v in enumerate(ter.westI):
            self.assertEqual(v, ter2.westI[i], i)

        self.assertGreater(len(ter.southI), 0)
        self.assertEqual(len(ter.southI), len(ter2.southI))
        for i, v in enumerate(ter.southI):
            self.assertEqual(v, ter2.southI[i], i)

        self.assertGreater(len(ter.eastI), 0)
        self.assertEqual(len(ter.eastI), len(ter2.eastI))
        for i, v in enumerate(ter.eastI):
            self.assertEqual(v, ter2.eastI[i], i)

        self.assertGreater(len(ter.northI), 0)
        self.assertEqual(len(ter.northI), len(ter2.northI))
        for i, v in enumerate(ter.northI):
            self.assertEqual(v, ter2.northI[i], i)

        self.assertEqual(ter2.getContentType(),
                         'application/vnd.quantized-mesh')

    def testWatermaskOnlyReader(self):
        z = 9
        x = 769
        y = 319
        geodetic = GlobalGeodetic(True)
        [minx, miny, maxx, maxy] = geodetic.TileBounds(x, y, z)

        ter = TerrainTile(west=minx, south=miny, east=maxx, north=maxy)
        ter.fromFile('tests/data/%s_%s_%s_watermask.terrain' % (z, x, y),
                     hasWatermask=True)

        self.assertEqual(len(ter.watermask), 256)
        for row in ter.watermask:
            self.assertEqual(len(row), 256)
            for val in row:
                self.assertGreaterEqual(val, 0)
                self.assertLessEqual(val, 255)

        ter.toFile(self.tmpfile)

        ter2 = TerrainTile(west=minx, south=miny, east=maxx, north=maxy)
        ter2.fromFile(self.tmpfile, hasWatermask=True)

        self.assertEqual(len(ter2.watermask), 256)

        for i in range(0, len(ter.watermask)):
            for j in range(0, len(ter.watermask[i])):
                self.assertEqual(ter.watermask[i][j], ter2.watermask[i][j])

        self.assertEqual(ter2.getContentType(),
                         'application/vnd.quantized-mesh;extensions=watermask')

    def testExtensionsReader(self):
        z = 10
        x = 1563
        y = 590
        geodetic = GlobalGeodetic(True)
        [minx, miny, maxx, maxy] = geodetic.TileBounds(x, y, z)

        ter = TerrainTile()
        ter = TerrainTile(west=minx, south=miny, east=maxx, north=maxy)
        ter.fromFile(
            'tests/data/%s_%s_%s_light_watermask.terrain' % (z, x, y),
            hasLighting=True, hasWatermask=True
        )

        # check indices
        self.assertGreater(len(ter.indices), 0)

        # check edges
        self.assertGreater(len(ter.westI), 0)
        self.assertGreater(len(ter.southI), 0)
        self.assertGreater(len(ter.eastI), 0)
        self.assertGreater(len(ter.northI), 0)

        # check extensions
        self.assertEqual(len(ter.watermask), 1)
        self.assertEqual(len(ter.watermask[0]), 1)
        # Water only -> 255
        self.assertEqual(ter.watermask[0][0], 255)
        ter.toFile(self.tmpfile)

        ter2 = TerrainTile(west=minx, south=miny, east=maxx, north=maxy)
        ter2.fromFile(self.tmpfile,
                      hasLighting=True, hasWatermask=True)

        self.assertEqual(len(ter.watermask), len(ter2.watermask))
        self.assertEqual(len(ter.watermask[0]), len(ter2.watermask[0]))

        sign = lambda a: 1 if a > 0 else -1 if a < 0 else 0
        for i in range(0, len(ter.vLight)):
            for j in range(0, 3):
                # We cannot have an exact equality with successive
                # oct encoding and decoding
                # Thus we only check the sign
                self.assertEqual(sign(ter.vLight[i][j]), sign(ter2.vLight[i][j]))

        self.assertEqual(ter2.getContentType(),
                         'application/vnd.quantized-mesh;' +
                         'extensions=octvertexnormals-watermask')

    def testExtentionsReaderWriterGzipped(self):
        z = 10
        x = 1563
        y = 590
        geodetic = GlobalGeodetic(True)
        [minx, miny, maxx, maxy] = geodetic.TileBounds(x, y, z)

        # Regular file not gzip compressed
        ter = TerrainTile()
        ter = TerrainTile(west=minx, south=miny, east=maxx, north=maxy)
        ter.fromFile(
            'tests/data/%s_%s_%s_light_watermask.terrain' % (z, x, y),
            hasLighting=True, hasWatermask=True
        )

        # Same file but gzipped this time
        terG = TerrainTile()
        terG = TerrainTile(west=minx, south=miny, east=maxx, north=maxy)
        terG.fromFile(
            'tests/data/%s_%s_%s_light_watermask.terrain.gz' % (z, x, y),
            hasLighting=True, hasWatermask=True, gzipped=True
        )

        # check indices
        self.assertEqual(len(terG.indices), len(ter.indices))
        self.assertEqual(terG.indices[0], ter.indices[0])

        # check edges
        self.assertEqual(len(terG.westI), len(ter.westI))
        self.assertEqual(len(terG.southI), len(ter.southI))
        self.assertEqual(len(terG.eastI), len(ter.eastI))
        self.assertEqual(len(terG.northI), len(ter.northI))

        self.assertEqual(terG.westI[0], ter.westI[0])
        self.assertEqual(terG.southI[0], ter.southI[0])
        self.assertEqual(terG.eastI[0], ter.eastI[0])
        self.assertEqual(terG.northI[0], ter.northI[0])

        self.assertEqual(len(terG.watermask), len(ter.watermask))
        self.assertEqual(len(terG.watermask[0]), len(ter.watermask[0]))
        # Water only -> 255
        self.assertEqual(terG.watermask[0][0], 255)
        # To gzipped file
        terG.toFile(self.tmpfile, gzipped=True)

    def testTileCreationFromTopology(self):
        wkts = [
            'POLYGON Z ((0.0 0.0 1.0, 0.0 1.0 1.0, 1.0 1.0 1.0, 0.0 0.0 1.0))',
            'POLYGON Z ((0.0 0.0 1.0, 1.0 0.0 1.0, 1.0 1.0 1.0, 0.0 0.0 1.0))'
        ]
        topology = TerrainTopology(geometries=wkts)
        tile = TerrainTile(topology=topology)

        # Check that the bounds are extracted from the terrain topology
        self.assertEqual(tile._west, 0.0)
        self.assertEqual(tile._south, 0.0)
        self.assertEqual(tile._east, 1.0)
        self.assertEqual(tile._north, 1.0)

        fileLike = tile.toBytesIO()
        self.assertIsInstance(fileLike, io.BytesIO)

    def testGzippedTileCreationFromTopology(self):
        wkts = [
            'POLYGON Z ((0.0 0.0 1.0, 0.0 1.0 1.0, 1.0 1.0 1.0, 0.0 0.0 1.0))',
            'POLYGON Z ((0.0 0.0 1.0, 1.0 0.0 1.0, 1.0 1.0 1.0, 0.0 0.0 1.0))'
        ]
        topology = TerrainTopology(geometries=wkts)
        tile = TerrainTile(topology=topology)

        # Check that the bounds are extracted from the terrain topology
        self.assertEqual(tile._west, 0.0)
        self.assertEqual(tile._south, 0.0)
        self.assertEqual(tile._east, 1.0)
        self.assertEqual(tile._north, 1.0)

        fileLike = tile.toBytesIO(gzipped=True)
        self.assertIsInstance(fileLike, io.BytesIO)

    def test_fromBytesIO(self):
        z = 10
        x = 1563
        y = 590
        geodetic = GlobalGeodetic(True)
        [minx, miny, maxx, maxy] = geodetic.TileBounds(x, y, z)

        # Regular file not gzip compressed
        ter = TerrainTile()
        ter = TerrainTile(west=minx, south=miny, east=maxx, north=maxy)
        with open('tests/data/%s_%s_%s_light_watermask.terrain' % (z, x, y), 'rb') as f:
            content = io.BytesIO(f.read())

        ter.fromBytesIO(content, hasLighting=True, hasWatermask=True)

        # check indices
        self.assertGreater(len(ter.indices), 0)

        # check edges
        self.assertGreater(len(ter.westI), 0)
        self.assertGreater(len(ter.southI), 0)
        self.assertGreater(len(ter.eastI), 0)
        self.assertGreater(len(ter.northI), 0)

        # check extensions
        self.assertEqual(len(ter.watermask), 1)
        self.assertEqual(len(ter.watermask[0]), 1)
        # Water only -> 255
        self.assertEqual(ter.watermask[0][0], 255)
