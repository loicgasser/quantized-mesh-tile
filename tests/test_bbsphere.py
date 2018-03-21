# -*- coding: utf-8 -*-
import os
from builtins import map
import unittest
import quantized_mesh_tile.cartesian3d as c3d
from quantized_mesh_tile.terrain import TerrainTile
from quantized_mesh_tile.llh_ecef import LLH2ECEF
from quantized_mesh_tile.bbsphere import BoundingSphere
from quantized_mesh_tile.global_geodetic import GlobalGeodetic


class TestBoundingSphere(unittest.TestCase):

    def testBoundingSphereAssign(self):
        center = [1, 3, 12]
        radius = 8
        sphere = BoundingSphere(center=center, radius=radius)
        self.assertEqual(sphere.center[0], 1.0)
        self.assertEqual(sphere.center[1], 3.0)
        self.assertEqual(sphere.center[2], 12.0)
        self.assertEqual(sphere.radius, 8.0)

    def testBoundingSphereFromPoints(self):
        sphere = BoundingSphere()
        self.assertEqual(len(sphere.center), 0)
        self.assertEqual(sphere.radius, 0.0)

        self.assertEqual(sphere.minPointX[0], float('inf'))
        self.assertEqual(sphere.minPointY[1], float('inf'))
        self.assertEqual(sphere.minPointZ[2], float('inf'))

        self.assertEqual(sphere.maxPointX[0], float('-inf'))
        self.assertEqual(sphere.maxPointY[1], float('-inf'))
        self.assertEqual(sphere.maxPointZ[2], float('-inf'))

        points = [[1.1, 3.2, 4.9],
                  [3.1, 1.0, 21.4],
                  [9.1, 3.2, 2.0],
                  [2.0, 4.0, 9.5]]
        sphere.fromPoints(points)

        self.assertNotEqual(sphere.minPointX[0], float('inf'))
        self.assertNotEqual(sphere.minPointY[1], float('inf'))
        self.assertNotEqual(sphere.minPointZ[2], float('inf'))

        self.assertNotEqual(sphere.maxPointX[0], float('-inf'))
        self.assertNotEqual(sphere.maxPointY[1], float('-inf'))
        self.assertNotEqual(sphere.maxPointZ[2], float('-inf'))

        for point in points:
            distance = c3d.distance(sphere.center, point)
            self.assertLessEqual(distance, sphere.radius)

        # Point outside the sphere
        pointOutside = [1000.0, 1000.0, 1000.0]
        distance = c3d.distance(sphere.center, pointOutside)
        self.assertGreater(distance, sphere.radius)

    def testBoundingSphereOnePoint(self):
        sphere = BoundingSphere()
        point = [[1.1, 3.2, 4.9]]

        with self.assertRaises(Exception):
            sphere.fromPoints(point)

    def testBoundingSpherePrecision(self):
        x = 533
        y = 383
        z = 9

        geodetic = GlobalGeodetic(True)
        [minx, miny, maxx, maxy] = geodetic.TileBounds(x, y, z)
        ter = TerrainTile(west=minx, south=miny, east=maxx, north=maxy)
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'data/%s_%s_%s.terrain' % (z, x, y))
        ter.fromFile(file_path)

        llh2ecef = lambda x: LLH2ECEF(x[0], x[1], x[2])
        coords = ter.getVerticesCoordinates()
        coords = list(map(llh2ecef, coords))
        sphere = BoundingSphere()
        sphere.fromPoints(coords)
        for coord in coords:
            distance = c3d.distance(sphere.center, coord)
            self.assertLessEqual(distance, sphere.radius)
