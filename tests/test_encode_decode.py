# -*- coding: utf-8 -*-

import os
import unittest
from quantized_mesh_tile import encode, decode
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
        self.tmpfile = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'data/temp.terrain')

    def tearDown(self):
        if os.path.exists(self.tmpfile):
            os.remove(self.tmpfile)

    def testEncodeDecode(self):
        z = 0
        x = 0
        y = 0
        globalGeodetic = GlobalGeodetic(True)
        bounds = globalGeodetic.TileBounds(x, y, z)
        ter = encode(geometries, bounds=bounds)
        ter.toFile(self.tmpfile)
        ter2 = decode(self.tmpfile, bounds)

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

        self.assertEqual(len(ter.eastI), 0)
        self.assertEqual(len(ter.eastI), len(ter2.eastI))
