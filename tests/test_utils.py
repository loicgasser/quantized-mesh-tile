# -*- coding: utf-8 -*-

import unittest
from quantized_mesh_tile.utils import octDecode, octEncode


class TestUtils(unittest.TestCase):

    def testOctDecode(self):
        vec3 = octDecode(0, 0)
        self.assertEqual(vec3[0], 0.0)
        self.assertEqual(vec3[1], 0.0)
        self.assertEqual(vec3[2], -1.0)

        vec3 = octDecode(255, 255)
        self.assertEqual(vec3[0], 0.0)
        self.assertEqual(vec3[1], 0.0)
        self.assertEqual(vec3[2], -1.0)

        vec3 = octDecode(255, 0)
        self.assertEqual(vec3[0], 0.0)
        self.assertEqual(vec3[1], 0.0)
        self.assertEqual(vec3[2], -1.0)

        vec3 = octDecode(0, 255)
        self.assertEqual(vec3[0], 0.0)
        self.assertEqual(vec3[1], 0.0)
        self.assertEqual(vec3[2], -1.0)

    def testOctDecodeErrors(self):
        with self.assertRaises(ValueError):
            octDecode(-1, 0)

        with self.assertRaises(ValueError):
            octDecode(0, -1)

        with self.assertRaises(ValueError):
            octDecode(256, 0)

        with self.assertRaises(ValueError):
            octDecode(0, 256)

    def testOctEncode(self):
        vec2 = octEncode([0.0, 0.0, -1.0])
        self.assertEqual(vec2[0], 255)
        self.assertEqual(vec2[1], 255)

        vec2 = octEncode([0.0, 0.0, 1.0])
        self.assertEqual(vec2[0], 128)
        self.assertEqual(vec2[1], 128)

    def testOctEncodeErrors(self):
        with self.assertRaises(ValueError):
            octEncode([2.0, 0.0, 0.0])

        with self.assertRaises(ValueError):
            octEncode([0.0, 0.0, 0.0])
