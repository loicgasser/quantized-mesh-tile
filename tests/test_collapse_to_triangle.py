# -*- coding: utf-8 -*-

import unittest

from shapely.geometry import Polygon

from quantized_mesh_tile.exceptions import InvalidGeometryError
from quantized_mesh_tile.utils import collapseIntoTriangles


class TestCollapseIntoTriangle(unittest.TestCase):
    """Test triangulation of polygons with more than 3 vertices.

    Uses Delaunay triangulation which guarantees non-overlapping triangles.
    Tests verify validity properties rather than exact triangle output.
    """

    def _verify_triangulation(self, coords, triangles):
        """Verify triangulation is valid."""
        # Check we have at least n-2 triangles (minimum for convex polygon)
        n_vertices = len(coords)
        min_triangles = n_vertices - 2
        self.assertGreaterEqual(
            len(triangles),
            min_triangles,
            f"Expected at least {min_triangles} triangles for {n_vertices} vertices",
        )

        # Check each triangle has 3 vertices
        for i, tri in enumerate(triangles):
            self.assertEqual(len(tri), 3, f"Triangle {i} should have 3 vertices")

        # Check no overlapping triangles (total area == convex hull area)
        total_area = sum(
            abs(Polygon([(v[0], v[1]) for v in tri]).area) for tri in triangles
        )
        hull_area = Polygon([(c[0], c[1]) for c in coords]).convex_hull.area
        self.assertAlmostEqual(
            total_area,
            hull_area,
            places=6,
            msg="Triangles should not overlap (total area should equal convex hull)",
        )

        # Check all original vertices are used
        original_vertices = {(c[0], c[1]) for c in coords}
        triangle_vertices = set()
        for tri in triangles:
            for v in tri:
                triangle_vertices.add((v[0], v[1]))
        self.assertEqual(
            original_vertices,
            triangle_vertices,
            "All original vertices should be in triangles",
        )

        # Check z-coordinates are preserved
        z_map = {(c[0], c[1]): c[2] for c in coords}
        for tri in triangles:
            for v in tri:
                key = (v[0], v[1])
                self.assertEqual(
                    v[2], z_map[key], f"Z-coordinate should be preserved for {key}"
                )

    def testCollapseThreeNodes(self):
        """Triangle input should return as-is."""
        coords = [[1, 1, 1], [1, 2, 1], [2, 1, 1]]
        triangles = collapseIntoTriangles(coords)
        self.assertEqual(len(triangles), 1)
        self.assertEqual(triangles[0], coords)

    def testCollapseFourNodes(self):
        """Quadrilateral should produce 2 triangles."""
        coords = [[1, 1, 1], [1, 2, 1], [2, 1, 1], [3, 2, 2]]
        triangles = collapseIntoTriangles(coords)
        self._verify_triangulation(coords, triangles)

    def testCollapseFiveNodes(self):
        """Pentagon should produce 3 triangles."""
        coords = [[1, 1, 1], [1, 2, 1], [2, 1, 1], [3, 2, 2], [2, 3, 3]]
        triangles = collapseIntoTriangles(coords)
        self._verify_triangulation(coords, triangles)

    def testCollapseSixNodes(self):
        """Hexagon should produce 4 triangles."""
        coords = [[1, 1, 1], [1, 2, 1], [2, 1, 1], [3, 2, 2], [2, 3, 3], [5, 2, 1]]
        triangles = collapseIntoTriangles(coords)
        self._verify_triangulation(coords, triangles)

    def testCollapseSevenNodes(self):
        """Heptagon should produce 5 triangles."""
        coords = [
            [1, 1, 1],
            [1, 2, 1],
            [2, 1, 1],
            [3, 2, 2],
            [2, 3, 3],
            [5, 2, 1],
            [6, 6, 6],
        ]
        triangles = collapseIntoTriangles(coords)
        self._verify_triangulation(coords, triangles)

    def testPreservesZCoordinates(self):
        """Z-coordinates (heights) should be preserved exactly."""
        coords = [
            [0, 0, 100.5],
            [1, 0, 200.25],
            [1, 1, 300.75],
            [0, 1, 150.125],
        ]
        triangles = collapseIntoTriangles(coords)

        # Build z-lookup from original coords
        z_lookup = {(c[0], c[1]): c[2] for c in coords}

        # Verify each triangle vertex has correct z
        for tri in triangles:
            for v in tri:
                expected_z = z_lookup[(v[0], v[1])]
                self.assertEqual(v[2], expected_z)

    def testDuplicateXYCoordinatesRaisesError(self):
        """Duplicate (x, y) coordinates should raise an error."""
        coords = [
            [0, 0, 100],
            [1, 0, 200],
            [1, 1, 300],
            [0, 0, 999],  # Same x,y as first point
        ]
        with self.assertRaises(InvalidGeometryError) as ctx:
            collapseIntoTriangles(coords)
        self.assertIn("Duplicate", str(ctx.exception))
