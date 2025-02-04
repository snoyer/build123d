"""
build123d tests

name: test_oriented_bound_box.py
by:   Gumyr
date: February 4, 2025

desc:
    This python module contains tests for the build123d project.

license:

    Copyright 2025 Gumyr

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

"""

import math
import re
import unittest

from build123d.geometry import Axis, OrientedBoundBox, Pos, Rot, Vector
from build123d.topology import Face, Solid


class TestOrientedBoundBox(unittest.TestCase):
    def test_size_and_diagonal(self):
        # Create a unit cube (with one corner at the origin).
        cube = Solid.make_box(1, 1, 1)
        obb = OrientedBoundBox(cube)

        # The size property multiplies half-sizes by 2. For a unit cube, expect (1, 1, 1).
        size = obb.size
        self.assertAlmostEqual(size.X, 1.0, places=6)
        self.assertAlmostEqual(size.Y, 1.0, places=6)
        self.assertAlmostEqual(size.Z, 1.0, places=6)

        # The full body diagonal should be sqrt(1^2+1^2+1^2) = sqrt(3).
        expected_diag = math.sqrt(3)
        self.assertAlmostEqual(obb.diagonal, expected_diag, places=6)

        obb.wrapped = None
        self.assertAlmostEqual(obb.diagonal, 0.0, places=6)

    def test_center(self):
        # For a cube made at the origin, the center should be at (0.5, 0.5, 0.5)
        cube = Solid.make_box(1, 1, 1)
        obb = OrientedBoundBox(cube)
        center = obb.center()
        self.assertAlmostEqual(center.X, 0.5, places=6)
        self.assertAlmostEqual(center.Y, 0.5, places=6)
        self.assertAlmostEqual(center.Z, 0.5, places=6)

    def test_directions_are_unit_vectors(self):
        # Create a rotated cube so the direction vectors are non-trivial.
        cube = Rot(45, 45, 0) * Solid.make_box(1, 1, 1)
        obb = OrientedBoundBox(cube)

        # Check that each primary direction is a unit vector.
        for direction in (obb.x_direction, obb.y_direction, obb.z_direction):
            self.assertAlmostEqual(direction.length, 1.0, places=6)

    def test_is_outside(self):
        # For a unit cube, test a point inside and a point clearly outside.
        cube = Solid.make_box(1, 1, 1)
        obb = OrientedBoundBox(cube)

        # Use the cube's center as an "inside" test point.
        center = obb.center()
        self.assertFalse(obb.is_outside(center))

        # A point far away should be outside.
        outside_point = Vector(10, 10, 10)
        self.assertTrue(obb.is_outside(outside_point))

        outside_point._wrapped = None
        with self.assertRaises(ValueError):
            obb.is_outside(outside_point)

    def test_is_completely_inside(self):
        # Create a larger cube and a smaller cube that is centered within it.
        large_cube = Solid.make_box(2, 2, 2)
        small_cube = Solid.make_box(1, 1, 1)
        # Translate the small cube by (0.5, 0.5, 0.5) so its center is at (1,1,1),
        # which centers it within the 2x2x2 cube (whose center is also at (1,1,1)).
        small_cube = Pos(0.5, 0.5, 0.5) * small_cube

        large_obb = OrientedBoundBox(large_cube)
        small_obb = OrientedBoundBox(small_cube)

        # The small box should be completely inside the larger box.
        self.assertTrue(large_obb.is_completely_inside(small_obb))
        # Conversely, the larger box cannot be completely inside the smaller one.
        self.assertFalse(small_obb.is_completely_inside(large_obb))

        large_obb.wrapped = None
        with self.assertRaises(ValueError):
            small_obb.is_completely_inside(large_obb)

    def test_init_from_bnd_obb(self):
        # Test that constructing from an already computed Bnd_OBB works as expected.
        cube = Solid.make_box(1, 1, 1)
        obb1 = OrientedBoundBox(cube)
        # Create a new instance by passing the underlying wrapped object.
        obb2 = OrientedBoundBox(obb1.wrapped)

        # Compare diagonal, size, and center.
        self.assertAlmostEqual(obb1.diagonal, obb2.diagonal, places=6)
        size1 = obb1.size
        size2 = obb2.size
        self.assertAlmostEqual(size1.X, size2.X, places=6)
        self.assertAlmostEqual(size1.Y, size2.Y, places=6)
        self.assertAlmostEqual(size1.Z, size2.Z, places=6)
        center1 = obb1.center()
        center2 = obb2.center()
        self.assertAlmostEqual(center1.X, center2.X, places=6)
        self.assertAlmostEqual(center1.Y, center2.Y, places=6)
        self.assertAlmostEqual(center1.Z, center2.Z, places=6)

    def test_plane(self):
        rect = Rot(Z=10) * Face.make_rect(1, 2)
        obb = rect.oriented_bounding_box()
        pln = obb.plane
        self.assertAlmostEqual(
            abs(pln.x_dir.dot(Vector(0, 1, 0).rotate(Axis.Z, 10))), 1.0, places=6
        )
        self.assertAlmostEqual(abs(pln.z_dir.dot(Vector(0, 0, 1))), 1.0, places=6)

    def test_repr(self):
        # Create a simple unit cube OBB.
        obb = OrientedBoundBox(Solid.make_box(1, 1, 1))
        rep = repr(obb)

        # Check that the repr string contains expected substrings.
        self.assertIn("OrientedBoundBox(center=Vector(", rep)
        self.assertIn("size=Vector(", rep)
        self.assertIn("plane=Plane(", rep)

        # Use a regular expression to extract numbers.
        pattern = (
            r"OrientedBoundBox\(center=Vector\((?P<c0>[-\d\.]+), (?P<c1>[-\d\.]+), (?P<c2>[-\d\.]+)\), "
            r"size=Vector\((?P<s0>[-\d\.]+), (?P<s1>[-\d\.]+), (?P<s2>[-\d\.]+)\), "
            r"plane=Plane\(o=\((?P<o0>[-\d\.]+), (?P<o1>[-\d\.]+), (?P<o2>[-\d\.]+)\), "
            r"x=\((?P<x0>[-\d\.]+), (?P<x1>[-\d\.]+), (?P<x2>[-\d\.]+)\), "
            r"z=\((?P<z0>[-\d\.]+), (?P<z1>[-\d\.]+), (?P<z2>[-\d\.]+)\)\)\)"
        )
        m = re.match(pattern, rep)
        self.assertIsNotNone(
            m, "The __repr__ string did not match the expected format."
        )

        # Convert extracted strings to floats.
        center = Vector(
            float(m.group("c0")), float(m.group("c1")), float(m.group("c2"))
        )
        size = Vector(float(m.group("s0")), float(m.group("s1")), float(m.group("s2")))
        # For a unit cube, we expect the center to be (0.5, 0.5, 0.5)
        self.assertAlmostEqual(center.X, 0.5, places=6)
        self.assertAlmostEqual(center.Y, 0.5, places=6)
        self.assertAlmostEqual(center.Z, 0.5, places=6)
        # And the full size to be approximately (1, 1, 1) (floating-point values may vary slightly).
        self.assertAlmostEqual(size.X, 1.0, places=6)
        self.assertAlmostEqual(size.Y, 1.0, places=6)
        self.assertAlmostEqual(size.Z, 1.0, places=6)


if __name__ == "__main__":
    unittest.main()
