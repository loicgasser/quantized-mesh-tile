# -*- coding: utf-8 -*-

import unittest
from quantized_mesh_tile.topology import TerrainTopology

# Must be defined counter clock wise order
vertices_1 = [
    [2.1,  3.1,  3.3],
    [1.2,  1.5,  4.2],
    [3.2,  2.2,  4.5]
]

wkt_1 = 'POLYGON Z ((2.1 3.1 3.3, 1.2 1.5 4.2, 3.2 2.2 4.5, 2.1 3.1 3.3))'

wkb_1 = b'\x01\x03\x00\x00\x80\x01\x00\x00\x00\x04\x00\x00\x00\xcd\xcc\xcc\xcc' \
        b'\xcc\xcc\x00@\xcd\xcc\xcc\xcc\xcc\xcc\x08@ffffff\n@333333\xf3?\x00\x00' \
        b'\x00\x00\x00\x00\xf8?\xcd\xcc\xcc\xcc\xcc\xcc\x10@\x9a\x99\x99\x99\x99' \
        b'\x99\t@\x9a\x99\x99\x99\x99\x99\x01@\x00\x00\x00\x00\x00\x00\x12@\xcd' \
        b'\xcc\xcc\xcc\xcc\xcc\x00@\xcd\xcc\xcc\xcc\xcc\xcc\x08@ffffff\n@'

vertices_2 = [
    [1.2,  1.5,  4.2],
    [2.2,  1.1,  1.1],
    [2.1,  2.2,  3.3]
]

wkt_2 = 'POLYGON Z ((1.2 1.5 4.2, 2.2 1.1 1.1, 2.1 2.2 3.3, 1.2 1.5 4.2))'

wkb_2 = b'\x01\x03\x00\x00\x80\x01\x00\x00\x00\x04\x00\x00\x00333333\xf3?\x00' \
        b'\x00\x00\x00\x00\x00\xf8?\xcd\xcc\xcc\xcc\xcc\xcc\x10@\x9a\x99\x99' \
        b'\x99\x99\x99\x01@\x9a\x99\x99\x99\x99\x99\xf1?\x9a\x99\x99\x99\x99' \
        b'\x99\xf1?\xcd\xcc\xcc\xcc\xcc\xcc\x00@\x9a\x99\x99\x99\x99\x99' \
        b'\x01@ffffff\n@333333\xf3?\x00\x00\x00\x00\x00\x00\xf8?\xcd\xcc\xcc' \
        b'\xcc\xcc\xcc\x10@'


class TestTopology(unittest.TestCase):

    def testTopologyOneVertex(self):
        topology = TerrainTopology()
        topology.addGeometries([vertices_1])

        topologyWKT = TerrainTopology()
        topologyWKT.addGeometries([wkt_1])

        topologyWKB = TerrainTopology()
        topologyWKB.addGeometries([wkb_1])

        self.assertIsInstance(topology.__repr__(), str)
        self.assertIsInstance(topology.__repr__(), str)
        self.assertIsInstance(topology.__repr__(), str)

        self.assertEqual(len(topology.vertices), 3)
        self.assertEqual(len(topology.faces), 1)

        self.assertEqual(topology.vertices[0][0], vertices_1[0][0])
        self.assertEqual(topology.vertices[0][1], vertices_1[0][1])
        self.assertEqual(topology.vertices[0][2], vertices_1[0][2])

        self.assertEqual(topology.vertices[1][0], vertices_1[1][0])
        self.assertEqual(topology.vertices[1][1], vertices_1[1][1])
        self.assertEqual(topology.vertices[1][2], vertices_1[1][2])

        # Test if from vertices and from wkt give the same result
        self.assertEqual(topology.vertices[0][0], topologyWKT.vertices[0][0])
        self.assertEqual(topology.vertices[0][1], topologyWKT.vertices[0][1])
        self.assertEqual(topology.vertices[0][2], topologyWKT.vertices[0][2])

        self.assertEqual(topology.vertices[1][0], topologyWKT.vertices[1][0])
        self.assertEqual(topology.vertices[1][1], topologyWKT.vertices[1][1])
        self.assertEqual(topology.vertices[1][2], topologyWKT.vertices[1][2])

        # Test if from wkt and from wkb give the same result
        self.assertEqual(topologyWKT.vertices[0][0], topologyWKB.vertices[0][0])
        self.assertEqual(topologyWKT.vertices[0][1], topologyWKB.vertices[0][1])
        self.assertEqual(topologyWKT.vertices[0][2], topologyWKB.vertices[0][2])

        self.assertEqual(topologyWKT.vertices[1][0], topologyWKB.vertices[1][0])
        self.assertEqual(topologyWKT.vertices[1][1], topologyWKB.vertices[1][1])
        self.assertEqual(topologyWKT.vertices[1][2], topologyWKB.vertices[1][2])

    def testTopologyTwoVertices(self):
        topology = TerrainTopology()
        topology.addGeometries([vertices_1, vertices_2])

        self.assertEqual(len(topology.vertices), 5)
        self.assertEqual(len(topology.faces), 2)

        # Make sure no extra vertice is inserted
        self.assertEqual(topology.vertices[1][0], vertices_2[0][0])
        self.assertEqual(topology.vertices[1][1], vertices_2[0][1])
        self.assertEqual(topology.vertices[1][2], vertices_2[0][2])

        self.assertEqual(topology.faces[1][0], 1)
        self.assertEqual(topology.faces[1][1], 3)
        self.assertEqual(topology.faces[1][2], 4)

        self.assertEqual(len(topology.indexData), 6)
        self.assertEqual(len(topology.uVertex), 5)
        self.assertEqual(len(topology.vVertex), 5)
        self.assertEqual(len(topology.hVertex), 5)

        self.assertEqual(topology.minLon, 1.2)
        self.assertEqual(topology.minLat, 1.1)
        self.assertEqual(topology.minHeight, 1.1)
        self.assertEqual(topology.maxLon, 3.2)
        self.assertEqual(topology.maxLat, 3.1)
        self.assertEqual(topology.maxHeight, 4.5)

    def testTopologyTwoVerticesConstructor(self):
        topology = TerrainTopology(geometries=[vertices_1, vertices_2])

        self.assertEqual(len(topology.vertices), 5)
        self.assertEqual(len(topology.faces), 2)

        # Make sure no extra vertice is inserted
        self.assertEqual(topology.vertices[1][0], vertices_2[0][0])
        self.assertEqual(topology.vertices[1][1], vertices_2[0][1])
        self.assertEqual(topology.vertices[1][2], vertices_2[0][2])

        self.assertEqual(topology.faces[1][0], 1)
        self.assertEqual(topology.faces[1][1], 3)
        self.assertEqual(topology.faces[1][2], 4)

        self.assertEqual(len(topology.indexData), 6)
        self.assertEqual(len(topology.uVertex), 5)
        self.assertEqual(len(topology.vVertex), 5)
        self.assertEqual(len(topology.hVertex), 5)

        self.assertEqual(topology.minLon, 1.2)
        self.assertEqual(topology.minLat, 1.1)
        self.assertEqual(topology.minHeight, 1.1)
        self.assertEqual(topology.maxLon, 3.2)
        self.assertEqual(topology.maxLat, 3.1)
        self.assertEqual(topology.maxHeight, 4.5)

    def testTopologyBadGeoms(self):
        wkt = 'POLYGON Z ((2.1 3.1 3.3, 1.2 1.5 4.2, 3.2 2.2 4.5, 2.5 1.2 1.1,' \
              ' 2.1 3.1 3.3))'
        with self.assertRaises(ValueError):
            TerrainTopology(geometries=[wkt])
        wkt = 'POLYGON ((2.1 3.1, 1.2 1.5, 3.2 2.2, 2.1 3.1))'
        with self.assertRaises(ValueError):
            TerrainTopology(geometries=[wkt])
        wkb = b'\x01\x03\x00\x00\x00\x01\x00\x00\x00\x04\x00\x00\x00\xcd\xcc' \
              b'\xcc\xcc\xcc\xcc\x00@\xcd\xcc\xcc\xcc\xcc\xcc\x08@333333\xf3?' \
              b'\x00\x00\x00\x00\x00\x00\xf8?\x9a\x99\x99\x99\x99\x99\t@\x9a' \
              b'\x99\x99\x99\x99\x99\x01@\xcd\xcc\xcc\xcc\xcc\xcc\x00@\xcd\xcc' \
              b'\xcc\xcc\xcc\xcc\x08@'
        with self.assertRaises(ValueError):
            TerrainTopology(geometries=[wkb])
        wkt = 'POINT (2.1 2.2)'
        with self.assertRaises(ValueError):
            TerrainTopology(geometries=[wkt])
        wktWrong = 'POLYGON Z ((2.1, 3.1 3.3, 1.2 1.5 4.2, 3.2 2.2, 4.5, 2.1 3.1 3.3))'
        with self.assertRaises(ValueError):
            TerrainTopology(geometries=[wktWrong])
