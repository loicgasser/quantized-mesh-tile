# -*- coding: utf-8 -*-

import unittest

from quantized_mesh_tile.utils import collapseIntoTriangles


def toString(t):
    return ','.join([str(i) for i in t])


class TestCollapseIntoTriangle(unittest.TestCase):

    def testCollapseFourNodes(self):
        coords = [
            [1, 1, 1],
            [1, 2, 1],
            [2, 1, 1],
            [3, 2, 2]
        ]
        triangles = collapseIntoTriangles(coords)
        self.assertEqual(len(triangles), 2)
        self.assertEqual(len(triangles[0]), 3)
        self.assertEqual(len(triangles[1]), 3)

        self.assertEqual(toString(triangles[0][0]), '1,1,1')
        self.assertEqual(toString(triangles[0][1]), '2,1,1')
        self.assertEqual(toString(triangles[0][2]), '1,2,1')

        self.assertEqual(toString(triangles[1][0]), '1,1,1')
        self.assertEqual(toString(triangles[1][1]), '2,1,1')
        self.assertEqual(toString(triangles[1][2]), '3,2,2')

    def testCollapseFiveNodes(self):
        coords = [
            [1, 1, 1],
            [1, 2, 1],
            [2, 1, 1],
            [3, 2, 2],
            [2, 3, 3]
        ]
        triangles = collapseIntoTriangles(coords)
        self.assertEqual(len(triangles), 3)
        self.assertEqual(len(triangles[0]), 3)
        self.assertEqual(len(triangles[1]), 3)
        self.assertEqual(len(triangles[2]), 3)

        self.assertEqual(toString(triangles[0][0]), '1,1,1')
        self.assertEqual(toString(triangles[0][1]), '2,1,1')
        self.assertEqual(toString(triangles[0][2]), '1,2,1')

        self.assertEqual(toString(triangles[1][0]), '1,1,1')
        self.assertEqual(toString(triangles[1][1]), '3,2,2')
        self.assertEqual(toString(triangles[1][2]), '2,1,1')

        self.assertEqual(toString(triangles[2][0]), '1,1,1')
        self.assertEqual(toString(triangles[2][1]), '3,2,2')
        self.assertEqual(toString(triangles[2][2]), '2,3,3')

    def testCollapseSixNodes(self):
        coords = [
            [1, 1, 1],
            [1, 2, 1],
            [2, 1, 1],
            [3, 2, 2],
            [2, 3, 3],
            [5, 2, 1]
        ]
        triangles = collapseIntoTriangles(coords)
        self.assertEqual(len(triangles), 4)
        self.assertEqual(len(triangles[0]), 3)
        self.assertEqual(len(triangles[1]), 3)
        self.assertEqual(len(triangles[2]), 3)
        self.assertEqual(len(triangles[3]), 3)

        self.assertEqual(toString(triangles[0][0]), '1,1,1')
        self.assertEqual(toString(triangles[0][1]), '2,1,1')
        self.assertEqual(toString(triangles[0][2]), '1,2,1')

        self.assertEqual(toString(triangles[1][0]), '3,2,2')
        self.assertEqual(toString(triangles[1][1]), '5,2,1')
        self.assertEqual(toString(triangles[1][2]), '2,3,3')

        self.assertEqual(toString(triangles[2][0]), '1,1,1')
        self.assertEqual(toString(triangles[2][1]), '3,2,2')
        self.assertEqual(toString(triangles[2][2]), '2,1,1')

        self.assertEqual(toString(triangles[3][0]), '1,1,1')
        self.assertEqual(toString(triangles[3][1]), '3,2,2')
        self.assertEqual(toString(triangles[3][2]), '5,2,1')

    def testCollapseSevenNodes(self):
        coords = [
            [1, 1, 1],
            [1, 2, 1],
            [2, 1, 1],
            [3, 2, 2],
            [2, 3, 3],
            [5, 2, 1],
            [6, 6, 6]
        ]
        triangles = collapseIntoTriangles(coords)
        self.assertEqual(len(triangles), 5)
        self.assertEqual(len(triangles[0]), 3)
        self.assertEqual(len(triangles[1]), 3)
        self.assertEqual(len(triangles[2]), 3)
        self.assertEqual(len(triangles[3]), 3)
        self.assertEqual(len(triangles[4]), 3)

        self.assertEqual(toString(triangles[0][0]), '1,1,1')
        self.assertEqual(toString(triangles[0][1]), '2,1,1')
        self.assertEqual(toString(triangles[0][2]), '1,2,1')

        self.assertEqual(toString(triangles[1][0]), '3,2,2')
        self.assertEqual(toString(triangles[1][1]), '5,2,1')
        self.assertEqual(toString(triangles[1][2]), '2,3,3')

        self.assertEqual(toString(triangles[2][0]), '1,1,1')
        self.assertEqual(toString(triangles[2][1]), '3,2,2')
        self.assertEqual(toString(triangles[2][2]), '2,1,1')

        self.assertEqual(toString(triangles[3][0]), '1,1,1')
        self.assertEqual(toString(triangles[3][1]), '5,2,1')
        self.assertEqual(toString(triangles[3][2]), '3,2,2')

        self.assertEqual(toString(triangles[4][0]), '1,1,1')
        self.assertEqual(toString(triangles[4][1]), '5,2,1')
        self.assertEqual(toString(triangles[4][2]), '6,6,6')
