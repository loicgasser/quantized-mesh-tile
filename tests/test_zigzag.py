# -*- coding: utf-8 -*-

import unittest

from quantized_mesh_tile.utils import zigZagDecode, zigZagEncode


class TestZigZag(unittest.TestCase):

    def testTo(self):
        self.assertEqual(zigZagEncode(-1), 1)
        self.assertEqual(zigZagEncode(-2), 3)
        self.assertEqual(zigZagEncode(0), 0)
        self.assertEqual(zigZagEncode(1), 2)
        self.assertEqual(zigZagEncode(2), 4)
        self.assertEqual(zigZagEncode(-1000000), 1999999)
        self.assertEqual(zigZagEncode(1000000), 2000000)

    def testBoth(self):
        self.assertEqual(-1, zigZagDecode(zigZagEncode(-1)))
        self.assertEqual(-2, zigZagDecode(zigZagEncode(-2)))
        self.assertEqual(0, zigZagDecode(zigZagEncode(0)))
        self.assertEqual(1, zigZagDecode(zigZagEncode(1)))
        self.assertEqual(2, zigZagDecode(zigZagEncode(2)))
        self.assertEqual(-10000, zigZagDecode(zigZagEncode(-10000)))
        self.assertEqual(10000, zigZagDecode(zigZagEncode(10000)))

        self.assertEqual(0, zigZagEncode(zigZagDecode(0)))
        self.assertEqual(1, zigZagEncode(zigZagDecode(1)))
        self.assertEqual(2, zigZagEncode(zigZagDecode(2)))
        self.assertEqual(2000000, zigZagEncode(zigZagDecode(2000000)))
