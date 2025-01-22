"""
build123d direct api tests

name: test_axis.py
by:   Gumyr
date: January 21, 2025

desc:
    This python module contains tests for the build123d project.

license:

    Copyright 2025 Gumyr

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

"""

import copy
import unittest

from OCP.gp import gp_Ax1, gp_Dir, gp_Pnt
from build123d.geometry import Axis, Location, Plane, Vector
from build123d.topology import Edge
from tests.base_test import DirectApiTestCase, AlwaysEqual


class TestAxis(DirectApiTestCase):
    """Test the Axis class"""

    def test_axis_init(self):
        test_axis = Axis((1, 2, 3), (0, 0, 1))
        self.assertVectorAlmostEquals(test_axis.position, (1, 2, 3), 5)
        self.assertVectorAlmostEquals(test_axis.direction, (0, 0, 1), 5)

        test_axis = Axis((1, 2, 3), direction=(0, 0, 1))
        self.assertVectorAlmostEquals(test_axis.position, (1, 2, 3), 5)
        self.assertVectorAlmostEquals(test_axis.direction, (0, 0, 1), 5)

        test_axis = Axis(origin=(1, 2, 3), direction=(0, 0, 1))
        self.assertVectorAlmostEquals(test_axis.position, (1, 2, 3), 5)
        self.assertVectorAlmostEquals(test_axis.direction, (0, 0, 1), 5)

        test_axis = Axis(Edge.make_line((1, 2, 3), (1, 2, 4)))
        self.assertVectorAlmostEquals(test_axis.position, (1, 2, 3), 5)
        self.assertVectorAlmostEquals(test_axis.direction, (0, 0, 1), 5)

        test_axis = Axis(edge=Edge.make_line((1, 2, 3), (1, 2, 4)))
        self.assertVectorAlmostEquals(test_axis.position, (1, 2, 3), 5)
        self.assertVectorAlmostEquals(test_axis.direction, (0, 0, 1), 5)

        with self.assertRaises(ValueError):
            Axis("one", "up")
        with self.assertRaises(ValueError):
            Axis(one="up")

    def test_axis_from_occt(self):
        occt_axis = gp_Ax1(gp_Pnt(1, 1, 1), gp_Dir(0, 1, 0))
        test_axis = Axis(occt_axis)
        self.assertVectorAlmostEquals(test_axis.position, (1, 1, 1), 5)
        self.assertVectorAlmostEquals(test_axis.direction, (0, 1, 0), 5)

    def test_axis_repr_and_str(self):
        self.assertEqual(repr(Axis.X), "((0.0, 0.0, 0.0),(1.0, 0.0, 0.0))")
        self.assertEqual(str(Axis.Y), "Axis: ((0.0, 0.0, 0.0),(0.0, 1.0, 0.0))")

    def test_axis_copy(self):
        x_copy = copy.copy(Axis.X)
        self.assertVectorAlmostEquals(x_copy.position, (0, 0, 0), 5)
        self.assertVectorAlmostEquals(x_copy.direction, (1, 0, 0), 5)
        x_copy = copy.deepcopy(Axis.X)
        self.assertVectorAlmostEquals(x_copy.position, (0, 0, 0), 5)
        self.assertVectorAlmostEquals(x_copy.direction, (1, 0, 0), 5)

    def test_axis_to_location(self):
        # TODO: Verify this is correct
        x_location = Axis.X.location
        self.assertTrue(isinstance(x_location, Location))
        self.assertVectorAlmostEquals(x_location.position, (0, 0, 0), 5)
        self.assertVectorAlmostEquals(x_location.orientation, (0, 90, 180), 5)

    def test_axis_located(self):
        y_axis = Axis.Z.located(Location((0, 0, 1), (-90, 0, 0)))
        self.assertVectorAlmostEquals(y_axis.position, (0, 0, 1), 5)
        self.assertVectorAlmostEquals(y_axis.direction, (0, 1, 0), 5)

    def test_axis_to_plane(self):
        x_plane = Axis.X.to_plane()
        self.assertTrue(isinstance(x_plane, Plane))
        self.assertVectorAlmostEquals(x_plane.origin, (0, 0, 0), 5)
        self.assertVectorAlmostEquals(x_plane.z_dir, (1, 0, 0), 5)

    def test_axis_is_coaxial(self):
        self.assertTrue(Axis.X.is_coaxial(Axis((0, 0, 0), (1, 0, 0))))
        self.assertFalse(Axis.X.is_coaxial(Axis((0, 0, 1), (1, 0, 0))))
        self.assertFalse(Axis.X.is_coaxial(Axis((0, 0, 0), (0, 1, 0))))

    def test_axis_is_normal(self):
        self.assertTrue(Axis.X.is_normal(Axis.Y))
        self.assertFalse(Axis.X.is_normal(Axis.X))

    def test_axis_is_opposite(self):
        self.assertTrue(Axis.X.is_opposite(Axis((1, 1, 1), (-1, 0, 0))))
        self.assertFalse(Axis.X.is_opposite(Axis.X))

    def test_axis_is_parallel(self):
        self.assertTrue(Axis.X.is_parallel(Axis((1, 1, 1), (1, 0, 0))))
        self.assertFalse(Axis.X.is_parallel(Axis.Y))

    def test_axis_angle_between(self):
        self.assertAlmostEqual(Axis.X.angle_between(Axis.Y), 90, 5)
        self.assertAlmostEqual(
            Axis.X.angle_between(Axis((1, 1, 1), (-1, 0, 0))), 180, 5
        )

    def test_axis_reverse(self):
        self.assertVectorAlmostEquals(Axis.X.reverse().direction, (-1, 0, 0), 5)

    def test_axis_reverse_op(self):
        axis = -Axis.X
        self.assertVectorAlmostEquals(axis.direction, (-1, 0, 0), 5)

    def test_axis_as_edge(self):
        edge = Edge(Axis.X)
        self.assertTrue(isinstance(edge, Edge))
        common = (edge & Edge.make_line((0, 0, 0), (1, 0, 0))).edge()
        self.assertAlmostEqual(common.length, 1, 5)

    def test_axis_intersect(self):
        common = (Axis.X.intersect(Edge.make_line((0, 0, 0), (1, 0, 0)))).edge()
        self.assertAlmostEqual(common.length, 1, 5)

        common = (Axis.X & Edge.make_line((0, 0, 0), (1, 0, 0))).edge()
        self.assertAlmostEqual(common.length, 1, 5)

        intersection = Axis.X & Axis((1, 0, 0), (0, 1, 0))
        self.assertVectorAlmostEquals(intersection, (1, 0, 0), 5)

        i = Axis.X & Axis((1, 0, 0), (1, 0, 0))
        self.assertEqual(i, Axis.X)

        intersection = Axis((1, 2, 3), (0, 0, 1)) & Plane.XY
        self.assertTupleAlmostEquals(intersection.to_tuple(), (1, 2, 0), 5)

        arc = Edge.make_circle(20, start_angle=0, end_angle=180)
        ax0 = Axis((-20, 30, 0), (4, -3, 0))
        intersections = arc.intersect(ax0).vertices().sort_by(Axis.X)
        self.assertTupleAlmostEquals(tuple(intersections[0]), (-5.6, 19.2, 0), 5)
        self.assertTupleAlmostEquals(tuple(intersections[1]), (20, 0, 0), 5)

        intersections = ax0.intersect(arc).vertices().sort_by(Axis.X)
        self.assertTupleAlmostEquals(tuple(intersections[0]), (-5.6, 19.2, 0), 5)
        self.assertTupleAlmostEquals(tuple(intersections[1]), (20, 0, 0), 5)

        i = Axis((0, 0, 1), (1, 1, 1)) & Vector(0.5, 0.5, 1.5)
        self.assertTrue(isinstance(i, Vector))
        self.assertVectorAlmostEquals(i, (0.5, 0.5, 1.5), 5)
        self.assertIsNone(Axis.Y & Vector(2, 0, 0))

        l = Edge.make_line((0, 0, 1), (0, 0, 2)) ^ 1
        i: Location = Axis.Z & l
        self.assertTrue(isinstance(i, Location))
        self.assertVectorAlmostEquals(i.position, l.position, 5)
        self.assertVectorAlmostEquals(i.orientation, l.orientation, 5)

        self.assertIsNone(Axis.Z & Edge.make_line((0, 0, 1), (1, 0, 0)).location_at(1))
        self.assertIsNone(Axis.Z & Edge.make_line((1, 0, 1), (1, 0, 2)).location_at(1))

        # TODO: uncomment when generalized edge to surface intersections are complete
        # non_planar = (
        #     Solid.make_cylinder(1, 10).faces().filter_by(GeomType.PLANE, reverse=True)
        # )
        # intersections = Axis((0, 0, 5), (1, 0, 0)) & non_planar

        # self.assertTrue(len(intersections.vertices(), 2))
        # self.assertTupleAlmostEquals(
        #     intersection.vertices()[0].to_tuple(), (-1, 0, 5), 5
        # )
        # self.assertTupleAlmostEquals(
        #     intersection.vertices()[1].to_tuple(), (1, 0, 5), 5
        # )

    def test_axis_equal(self):
        self.assertEqual(Axis.X, Axis.X)
        self.assertEqual(Axis.Y, Axis.Y)
        self.assertEqual(Axis.Z, Axis.Z)
        self.assertEqual(Axis.X, AlwaysEqual())

    def test_axis_not_equal(self):
        self.assertNotEqual(Axis.X, Axis.Y)
        random_obj = object()
        self.assertNotEqual(Axis.X, random_obj)


if __name__ == "__main__":
    import unittest

    unittest.main()
