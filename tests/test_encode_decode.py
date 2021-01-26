# -*- coding: utf-8 -*-

import os
import unittest

from quantized_mesh_tile import decode, encode
from quantized_mesh_tile.global_geodetic import GlobalGeodetic

# Partial tile
geometries = [
    ((-168.755, -33.753, 15.793),
     (-180.0, -45.004, 3.1),
     (-157.504, -45.004, -7.144)),
    ((-180.0, -33.753, 38.954),
     (-180.0, -45.004, 3.1),
     (-168.755, -33.753, 15.793)),
    ((-180.0, -33.753, 38.954),
     (-168.755, -33.753, 15.793),
     (-180.0, -22.503, 50.312))
]


class TestTopology(unittest.TestCase):

    def setUp(self):
        self.tmpfile = 'tests/data/temp.terrain'

    def tearDown(self):
        if os.path.exists(self.tmpfile):
            os.remove(self.tmpfile)

    def assert_tile(self, ter, ter2):
        self.assertIsInstance(ter.__repr__(), str)
        self.assertIsInstance(ter2.__repr__(), str)

        # check headers
        self.assertGreater(len(ter.header), 0)
        self.assertEqual(len(ter.header), len(ter2.header))

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

    def testEncodeDecode(self):
        z = 0
        x = 0
        y = 0
        globalGeodetic = GlobalGeodetic(True)
        bounds = globalGeodetic.TileBounds(x, y, z)
        ter = encode(geometries, bounds=bounds)
        ter.toFile(self.tmpfile)
        ter2 = decode(self.tmpfile, bounds)
        self.assert_tile(ter, ter2)
        # Partial tile nothing on the east edge
        self.assertEqual(len(ter.eastI), 0)
        self.assertEqual(len(ter.eastI), len(ter2.eastI))

    def testEncodeDecodeNoBounds(self):
        ter = encode(geometries)
        ter.toFile(self.tmpfile)
        bounds = ter.bounds
        ter2 = decode(self.tmpfile, bounds)
        self.assert_tile(ter, ter2)
        # Bounds computed dynamically from partial tile
        # east edge now has data
        self.assertGreater(len(ter.eastI), 0)
        self.assertEqual(len(ter.eastI), len(ter2.eastI))
